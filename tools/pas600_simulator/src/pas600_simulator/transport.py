"""Standalone verified-host SFTP transport, durable journal and per-destination/publisher cadence.

No backend imports or acceptance guesses. Every attempt freezes bytes, records CLOSE
facts separately from session ending, and aborts without a clean EOF on any failure.
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import UTC,datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import time
from typing import Literal
from uuid import uuid4
import asyncssh
from pydantic import BaseModel,ConfigDict,Field,model_validator
from pas600_simulator.journal import atomic_json,LocalRun


class Auth(BaseModel):
    """Exactly one external credential source, never an inline password."""
    model_config=ConfigDict(extra='forbid',hide_input_in_errors=True)
    password_env:str|None=Field(default=None,pattern=r'^[A-Z_][A-Z0-9_]*$')
    private_key_file:Path|None=None
    passphrase_env:str|None=Field(default=None,pattern=r'^[A-Z_][A-Z0-9_]*$')

    @model_validator(mode='after')
    def exclusive(self):
        """Require exactly one authentication mode and a meaningful private-key passphrase source."""
        if bool(self.password_env)==bool(self.private_key_file) or self.passphrase_env and not self.private_key_file:
            raise ValueError('invalid_auth_source')
        return self


class TransportSettings(BaseModel):
    """Closed transport configuration; limits cannot reduce the mandatory publication interval."""
    model_config=ConfigDict(extra='forbid',hide_input_in_errors=True)
    destination_alias:str=Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    host:str=Field(min_length=1,max_length=253)
    port:int=Field(default=2222,ge=1,le=65535,strict=True)
    directory:str='/'
    username:str=Field(min_length=1,max_length=80)
    known_hosts_file:Path
    auth:Auth
    publication_gap_seconds:int=Field(default=900,ge=900,strict=True)
    max_attempts:int=Field(default=3,ge=1,strict=True)
    connect_timeout_seconds:float=Field(default=30,gt=0,allow_inf_nan=False)
    operation_timeout_seconds:float=Field(default=60,gt=0,allow_inf_nan=False)
    attempt_timeout_seconds:float=Field(default=300,gt=0,allow_inf_nan=False)

    @model_validator(mode='after')
    def safe_directory(self):
        """Keep native names under one explicit virtual directory without traversal or control characters."""
        if not self.directory.startswith('/') or '..' in self.directory.split('/') or '\\' in self.directory or any(ord(c)<32 for c in self.directory):
            raise ValueError('invalid_directory')
        return self


class TransferError(Exception):
    """Fixed transport code and permanence, excluding remote diagnostics and credential material."""
    def __init__(self,code,permanent=False):
        """Store only an internal bounded code; never attach the original transport exception."""
        self.code,self.permanent=code,permanent
        super().__init__(code)


class Cadence:
    """Monotonic wait in-process and a full new wait after restart whenever any prior attempt exists."""
    def __init__(self,path,gap,monotonic=time.monotonic):
        """Read a locked persistent marker; no UTC difference can shorten the mandatory wait."""
        self.path,self.gap,self.monotonic=Path(path),gap,monotonic
        self.deadline=monotonic()+gap if self.path.exists() else monotonic()

    def remaining(self):
        """Return seconds until next permitted start, independent of wall-clock movement."""
        return max(0,self.deadline-self.monotonic())

    def started(self):
        """Persist an attempt marker before networking so a crash cannot erase cadence evidence."""
        atomic_json(self.path,{'state':'active','at':datetime.now(UTC).isoformat()})

    def finished(self):
        """Start the gap at the end of the complete attempt, including failed and slow ones."""
        self.deadline=self.monotonic()+self.gap
        atomic_json(self.path,{'state':'finished','at':datetime.now(UTC).isoformat()})


@asynccontextmanager
async def destination_lock(settings,publisher,stop):
    """Hold an OS lock across waiting/networking; serialize all runs for one destination alias and publisher."""
    root=Path(os.environ.get('PAS600_SIM_STATE_DIRECTORY',Path.home()/'.local/state/ecs-ec-pas600'))
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    key=hashlib.sha256(json.dumps([settings.destination_alias,publisher],separators=(',',':')).encode()).hexdigest()
    stream=(root/(key+'.lock')).open('a+b')
    try:
        while True:
            try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if stop.is_set():raise asyncio.CancelledError()
                await asyncio.sleep(.1)
        yield Cadence(root/(key+'.json'),settings.publication_gap_seconds)
    finally:
        stream.close()


def credentials(settings):
    """Resolve external credentials into connect-only memory, checking key permissions and mandatory known_hosts."""
    if not settings.known_hosts_file.is_file():raise TransferError('host_key_configuration',True)
    if settings.auth.password_env:
        password=os.environ.get(settings.auth.password_env)
        if not password:raise TransferError('credential_configuration',True)
        return dict(password=password,client_keys=[])
    key=settings.auth.private_key_file
    if not key.is_file() or key.stat().st_mode&0o077:raise TransferError('credential_configuration',True)
    passphrase=os.environ.get(settings.auth.passphrase_env) if settings.auth.passphrase_env else None
    if settings.auth.passphrase_env and not passphrase:raise TransferError('credential_configuration',True)
    return dict(client_keys=[str(key)],passphrase=passphrase)


def frozen_files(root,publication):
    """Read and verify exactly the manifest's native files into immutable bytes before any connection."""
    directory=root/'data'/publication['key']
    files=[]
    expected=set()
    for item in publication['files']:
        name=item['name']
        if PurePosixPath(name).name!=name or name in ('.','..') or '\\' in name or name in expected:raise TransferError('manifest_conflict',True)
        path=directory/name
        if path.is_symlink() or not path.is_file():raise TransferError('manifest_conflict',True)
        data=path.read_bytes()
        if len(data)!=item['size'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise TransferError('manifest_conflict',True)
        files.append((name,data));expected.add(name)
    if directory.is_symlink() or {p.name for p in directory.iterdir()}!=expected:raise TransferError('manifest_conflict',True)
    return files


async def transfer(settings,files,record,probe=False):
    """Execute one bounded attempt; only a fully successful transfer sends the subsystem's explicit EOF."""
    connection=None
    try:
        auth=credentials(settings)
        async with asyncio.timeout(settings.attempt_timeout_seconds):
            connection=await asyncio.wait_for(asyncssh.connect(settings.host,settings.port,username=settings.username,
                known_hosts=str(settings.known_hosts_file),**auth),settings.connect_timeout_seconds)
            sftp=await asyncio.wait_for(connection.start_sftp_client(),settings.operation_timeout_seconds)
            for name,data in files:
                path=str(PurePosixPath(settings.directory)/name)
                item={'name':name,'file_status':'pending'}
                record['files'].append(item)
                stream=await asyncio.wait_for(sftp.open(path,'xb',encoding=None),settings.operation_timeout_seconds)
                await asyncio.wait_for(stream.write(data),settings.operation_timeout_seconds)
                await asyncio.wait_for(stream.close(),settings.operation_timeout_seconds)
                item['file_status']='transferred'
                if probe:await asyncio.wait_for(sftp.remove(path),settings.operation_timeout_seconds)
            # SFTPClient.exit explicitly writes CHANNEL_EOF; never use its context-manager cleanup on failure.
            sftp.exit()
            await asyncio.wait_for(sftp.wait_closed(),settings.operation_timeout_seconds)
            record['session_end']='clean'
            record['publication_status']='transferred'
    except TransferError:
        record['session_end']='aborted';raise
    except (asyncssh.HostKeyNotVerifiable,asyncssh.PermissionDenied,asyncssh.SFTPPermissionDenied) as error:
        record['session_end']='aborted';raise TransferError('identity_rejected',True) from None
    except asyncssh.SFTPError:
        record['session_end']='aborted';raise TransferError('permission_or_resource_limit',True) from None
    except (OSError,asyncssh.Error,TimeoutError):
        record['session_end']='unknown';raise TransferError('transport_unavailable') from None
    finally:
        if record['session_end']!='clean':
            for item in record['files']:
                if item['file_status']=='pending':item['file_status']='failed'
        if connection:
            if record['session_end']!='clean':connection.abort()
            else:connection.close()
            await connection.wait_closed()


async def test_connection(settings):
    """Authenticate, verify host and write/delete the reserved probe without publishing native measurements."""
    record={'files':[],'session_end':'unknown','publication_status':'pending'}
    await transfer(settings,[('.ecs-ec-probe',b'probe')],record,probe=True)
    return {'schema_version':1,'status':'connected','destination_alias':settings.destination_alias,'port':settings.port}


async def publish_run(root,settings,*,resume=False,publication_key=None,stop=None):
    """Serialize mutations of one run even across destination aliases, then read its current durable journal.

    A second publisher must reread completed facts after the first releases the lock;
    an interrupted waiter owns no attempt and must not overwrite the active owner's run state.
    """
    root=Path(root);stop=stop or asyncio.Event()
    with (root/'control/.publish.lock').open('a+b') as lock:
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
            except BlockingIOError:
                if stop.is_set():return {'schema_version':1,'status':'stopped','exit_code':130}
                await asyncio.sleep(.1)
        return await _publish_run(root,settings,resume=resume,publication_key=publication_key,stop=stop)


async def _publish_run(root,settings,*,resume=False,publication_key=None,stop=None):
    """Publish frozen complete cycles with persistent ordinal budgets, cooperative stop and crash-safe cadence."""
    root=Path(root)
    stop=stop or asyncio.Event()
    manifest=json.loads((root/'control/manifest.json').read_text())
    scenario=json.loads((root/'control/scenario.safe.json').read_text())
    publications=manifest['publications']
    if {p.name for p in (root/'data').iterdir()}!={p['key'] for p in publications}:raise TransferError('manifest_conflict',True)
    frozen={p['key']:frozen_files(root,p) for p in publications}
    if publication_key is not None and publication_key not in frozen:raise TransferError('publication_not_found',True)
    journal=root/'control/transfers.jsonl'
    attempts=[json.loads(line) for line in journal.read_text().splitlines()] if journal.exists() else []
    pending=root/'control/transfers.pending.json'
    if pending.exists():attempts=json.loads(pending.read_text())['attempts']
    if attempts and not resume and publication_key is None:raise TransferError('resume_required',True)
    run=LocalRun.model_validate_json((root/'control/run.json').read_text())
    # Do not trust a mutable journal's paths as permission to write outside the supplied run.
    run.control_path=str(root/'control');run.data_path=str(root/'data')
    generation=uuid4().hex if publication_key else None
    async def save(record):
        """Atomically rewrite complete attempt facts before networking and after each attempt, preserving ordinal history."""
        temporary=root/'control/transfers.pending.json'
        atomic_json(temporary,{'attempts':attempts})
        # The JSONL export is replaced atomically; pending is the authoritative crash recovery copy.
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(mode='w',dir=journal.parent,delete=False,encoding='utf-8') as stream:
            for item in attempts:stream.write(json.dumps(item,sort_keys=True)+'\n')
            stream.flush();os.fsync(stream.fileno());name=stream.name
        os.replace(name,journal)
    pending=root/'control/transfers.pending.json'
    if pending.exists():attempts=json.loads(pending.read_text())['attempts']
    publisher=scenario['publisher']['publisher_serial']
    try:
        async with destination_lock(settings,publisher,stop) as cadence:
            for publication in publications:
                key=publication['key']
                if publication_key and key!=publication_key:continue
                previous=[a for a in attempts if a['publication']==key]
                current_generation=generation if publication_key else previous[-1].get('generation') if previous else None
                budget=[a for a in previous if a.get('generation')==current_generation]
                if not publication_key and any(a['publication_status']=='transferred' for a in budget):continue
                if len(budget)>=settings.max_attempts:raise TransferError('attempts_exhausted')
                for _ in range(settings.max_attempts-len(budget)):
                    if stop.is_set():raise asyncio.CancelledError()
                    if cadence.remaining():
                        try:await asyncio.wait_for(stop.wait(),cadence.remaining())
                        except TimeoutError:pass
                        if stop.is_set():raise asyncio.CancelledError()
                    record=dict(id=str(uuid4()),publication=key,generation=current_generation,ordinal=len(previous)+1,
                        started_at=datetime.now(UTC).isoformat(),ended_at=None,duration_seconds=None,
                        destination_alias=settings.destination_alias,port=settings.port,
                        files=[],session_end='unknown',publication_status='pending',failure_code=None)
                    attempts.append(record);previous.append(record)
                    run.state='publishing';run.save();await save(record)
                    cadence.started();started=time.monotonic();failure=None
                    try:
                        await transfer(settings,frozen[key],record)
                    except TransferError as error:
                        failure=error;record['failure_code']=error.code
                        record['publication_status']='uncertain' if record['session_end']=='unknown' else 'failed'
                    finally:
                        record['ended_at']=datetime.now(UTC).isoformat();record['duration_seconds']=time.monotonic()-started
                        cadence.finished();record['next_wait_seconds']=settings.publication_gap_seconds
                        await save(record)
                    if stop.is_set():raise asyncio.CancelledError()
                    if not failure:break
                    if failure.permanent:raise failure
                else:raise TransferError('attempts_exhausted')
            run.state='completed';run.save()
            return {'schema_version':1,'status':'transferred','attempts':len(attempts)}
    except asyncio.CancelledError:
        run.state='stopped';run.save();return {'schema_version':1,'status':'stopped','exit_code':130}
    except Exception:
        run.state='failed';run.save();raise
