"""SFTP staging with durable explicit CLOSE, contiguous writes and EOF-only publication commit."""
from dataclasses import dataclass
from pathlib import Path,PurePosixPath
from uuid import uuid4
import hashlib
import os
import re
from sqlalchemy import func,select
from ecs_ec.acquisition.models import AcquisitionBinding,SftpSessionAttempt,ReceivedFile,NativePublication,PublicationEvaluation
from ecs_ec.acquisition.audit import append_audit
from ecs_ec.acquisition.store import binding_lock,digest
from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.core.retention import anniversary

NATIVE_NAME=re.compile(r'^(?:[^/\\\x00]{1,210}_)?[0-9]{17}_[1-9][0-9]*\.(?:csv|json)$')


@dataclass
class FileHandle:
    """One private open file and contiguous-prefix cursor, never a shared filesystem path from the client."""
    identifier:object
    stream:object
    name:str
    offset:int=0
    probe:bool=False


class Staging:
    """One authenticated binding/session; every error irreversibly prevents sealing this session."""

    def __init__(self,database,clock,settings,binding):
        """Bind trusted resources; allocate no session until the authenticated subsystem is started."""
        self.database,self.clock,self.settings,self.binding=database,clock,settings,binding
        self.id=uuid4();self.handles={};self.failed=False;self.clean_eof=False;self.cleanup=False
        self.bytes=0;self.started=False

    async def start(self):
        """Create a durable receiving session under the current binding revision and active-session quota."""
        async with UnitOfWork(self.database.sessions) as uow:
            await binding_lock(uow,self.binding.id)
            current=(await uow.session.scalars(select(AcquisitionBinding).where(AcquisitionBinding.id==self.binding.id).order_by(AcquisitionBinding.revision.desc()).limit(1))).first()
            if not current or not current.enabled or current.revision!=self.binding.revision:raise ValueError('binding_changed')
            count=await uow.session.scalar(select(func.count()).select_from(SftpSessionAttempt).where(SftpSessionAttempt.binding_id==self.binding.id,SftpSessionAttempt.state=='receiving'))
            if count>=2:raise ValueError('resource_limit')
            uow.session.add(SftpSessionAttempt(id=self.id,binding_id=self.binding.id,binding_revision=self.binding.revision,
                state='receiving',correlation_ref=uuid4(),recorded_at=self.clock.now(),retain_until=anniversary(self.clock.now(),self.binding.timezone)))
            await uow.commit()
        root=self.settings.storage/self.id.hex
        root.mkdir(parents=True,mode=0o700,exist_ok=False)
        self.started=True

    def name(self,path):
        """Validate one native basename under the configured virtual directory; no traversal or guessed filesystem mapping."""
        if isinstance(path,bytes):path=path.decode('utf-8')
        if any(ord(char)<32 or ord(char)==127 for char in path) or '\\' in path or '\x00' in path or any(p in ('.','..') for p in path.split('/')):raise ValueError('invalid_path')
        parent=str(PurePosixPath(path).parent)
        allowed=self.binding.directory.rstrip('/') or '/'
        if parent not in ('.',allowed):raise ValueError('invalid_path')
        name=PurePosixPath(path).name
        if name!='.ecs-ec-probe' and (len(name.encode())>255 or not NATIVE_NAME.fullmatch(name)):raise ValueError('invalid_native_name')
        return name

    async def open(self,path):
        """Reserve a new file and publisher write slot before exposing an exclusive private descriptor."""
        try:
            if len(self.handles)>=self.settings.max_files:raise ValueError('resource_limit')
            name=self.name(path)
            probe=name=='.ecs-ec-probe'
            identifier=uuid4()
            async with UnitOfWork(self.database.sessions) as uow:
                await binding_lock(uow,self.binding.id)
                others=await uow.session.scalar(select(ReceivedFile.id).join(SftpSessionAttempt,ReceivedFile.session_id==SftpSessionAttempt.id).where(
                    SftpSessionAttempt.binding_id==self.binding.id,SftpSessionAttempt.state=='receiving',SftpSessionAttempt.id!=self.id))
                if others:raise ValueError('publisher_busy')
                count=await uow.session.scalar(select(func.count()).select_from(ReceivedFile).where(ReceivedFile.session_id==self.id))
                if count>=self.settings.max_files:raise ValueError('resource_limit')
                if not probe:
                    uow.session.add(ReceivedFile(id=identifier,session_id=self.id,name=name,storage_key=f'{self.id.hex}/{identifier.hex}',
                        state='writing',parse_status='pending',explicit_close=False,size=0,written_offset=0,
                        recorded_at=self.clock.now(),retain_until=anniversary(self.clock.now(),self.binding.timezone)))
                    await uow.commit()
            stream=open(self.settings.storage/self.id.hex/identifier.hex,'xb',buffering=0)
            os.chmod(stream.name,0o600)
            handle=FileHandle(identifier,stream,name,probe=probe)
            self.handles[identifier]=handle
            return handle
        except Exception:
            self.failed=True;raise

    async def write(self,handle,offset,data):
        """Write only the next contiguous prefix, enforcing file/session quotas before touching bytes."""
        try:
            limit=64 if handle.probe else self.settings.max_json_bytes if handle.name.endswith('.json') else self.settings.max_csv_bytes
            if handle.identifier not in self.handles or offset!=handle.offset or offset+len(data)>limit or self.bytes+len(data)>self.settings.max_session_bytes:
                raise ValueError('resource_limit')
            written=handle.stream.write(data)
            if written!=len(data):raise OSError('incomplete_write')
            handle.offset+=written;self.bytes+=written
        except Exception:
            self.failed=True;raise

    async def close(self,handle):
        """Fsync before explicit CLOSE OK; library cleanup is aborted evidence rather than successful client close."""
        try:
            handle.stream.flush();os.fsync(handle.stream.fileno());handle.stream.close()
            directory=os.open(Path(handle.stream.name).parent,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(directory)
            finally:os.close(directory)
            self.handles.pop(handle.identifier,None)
            if handle.probe:
                Path(handle.stream.name).unlink(missing_ok=True);return
            async with UnitOfWork(self.database.sessions) as uow:
                row=await uow.session.get(ReceivedFile,handle.identifier,with_for_update=True)
                row.size=row.written_offset=handle.offset
                row.sha256=hashlib.sha256(Path(handle.stream.name).read_bytes()).hexdigest()
                row.explicit_close=not self.cleanup
                row.state='closed' if row.explicit_close else 'aborted'
                await uow.commit()
        except Exception:
            self.failed=True;raise

    async def finish(self):
        """Seal the full closed manifest only after real CHANNEL_EOF; all other endings retain aborted evidence."""
        if not self.started:return None
        async with UnitOfWork(self.database.sessions) as uow:
            await binding_lock(uow,self.binding.id)
            session=await uow.session.get(SftpSessionAttempt,self.id,with_for_update=True)
            if session.state!='receiving':return session.publication_id
            files=(await uow.session.scalars(select(ReceivedFile).where(ReceivedFile.session_id==self.id).order_by(ReceivedFile.name))).all()
            valid=self.clean_eof and not self.failed and not self.handles and files and all(f.state=='closed' and f.explicit_close for f in files)
            # Observable native sequence gaps can be rejected, but the last index never proves completeness.
            groups={}
            for file in files:
                stem,ordinal=file.name.rsplit('_',1)
                groups.setdefault(stem,[]).append(int(ordinal.split('.')[0]))
            if any(sorted(numbers)!=list(range(1,len(numbers)+1)) for numbers in groups.values()):valid=False
            if not valid:
                session.state,session.reason='aborted','incomplete_session' if files else 'empty_or_probe'
                for file in files:file.state='aborted'
                phase='aborted'
            else:
                manifest=[dict(name=f.name,size=f.size,sha256=f.sha256) for f in files]
                fingerprint=digest(manifest)
                publication=await uow.session.scalar(select(NativePublication).where(NativePublication.binding_id==self.binding.id,
                    NativePublication.binding_revision==self.binding.revision,NativePublication.manifest_digest==fingerprint))
                if publication and publication.manifest!=manifest:raise ValueError('manifest_conflict')
                if not publication:
                    identifier=uuid4()
                    publication=NativePublication(id=identifier,binding_id=self.binding.id,binding_revision=self.binding.revision,
                        publication_ref='publication:'+identifier.hex,publisher=self.binding.publisher_serial,profile_id=self.binding.profile_id,
                        manifest=manifest,manifest_digest=fingerprint,sealed_at=self.clock.now(),state='queued',
                        recorded_at=self.clock.now(),retain_until=anniversary(self.clock.now(),self.binding.timezone))
                    uow.session.add(publication);await uow.session.flush()
                session.manifest,session.publication_id,session.state=manifest,publication.id,'sealed'
                for file in files:file.state='sealed'
                uow.session.add(PublicationEvaluation(publication_id=publication.id,session_id=session.id,correlation_ref=session.correlation_ref,
                    state='pending',recorded_at=self.clock.now(),retain_until=anniversary(self.clock.now(),self.binding.timezone)))
                phase='sealed'
            session.ended_at=self.clock.now()
            await append_audit(uow,self.clock,self.binding.timezone,phase,session.id)
            await uow.commit()
            return session.publication_id
