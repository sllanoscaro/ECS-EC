"""003 transaction helpers and PostgreSQL coordination; no locks remain held while calling002."""
import hashlib
import json
from sqlalchemy import select,text
from ecs_ec.acquisition.models import AcquisitionBinding,SftpSessionAttempt,ReceivedFile,PublicationEvaluation
from ecs_ec.core.unit_of_work import UnitOfWork


def digest(value):
    """SHA256 a canonical typed JSON value; callers still compare full manifests and frozen inputs."""
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


async def binding_lock(uow,binding_id):
    """Serialize one binding's session/ledger transitions using a PostgreSQL transaction lock across processes."""
    number=int.from_bytes(hashlib.sha256(binding_id.bytes).digest()[:8],'big',signed=True)
    await uow.session.execute(text('SELECT pg_advisory_xact_lock(:key)'),{'key':number})


async def abort_receiving(database,clock):
    """At exclusive listener startup abort unsealed sessions; never promote bytes based on size or parser success."""
    async with UnitOfWork(database.sessions) as uow:
        rows=(await uow.session.scalars(select(SftpSessionAttempt).where(SftpSessionAttempt.state=='receiving').with_for_update())).all()
        for row in rows:
            row.state,row.reason,row.ended_at='aborted','process_interrupted',clock.now()
            files=(await uow.session.scalars(select(ReceivedFile).where(ReceivedFile.session_id==row.id))).all()
            for file in files:file.state='aborted'
        await uow.commit()
