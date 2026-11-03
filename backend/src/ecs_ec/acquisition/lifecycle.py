"""Optional003 listener and supervised recovery in the common Uvicorn lifespan, never a separate worker."""
import asyncio
from contextlib import asynccontextmanager,suppress
from sqlalchemy import select,text
from ecs_ec.core.lifecycle import Module
from ecs_ec.acquisition.config import AcquisitionSettings
from ecs_ec.acquisition.models import AcquisitionBinding
from ecs_ec.acquisition.schemas import BindingInput
from ecs_ec.acquisition.service import Acquisition
from ecs_ec.acquisition.store import abort_receiving
from ecs_ec.acquisition.sftp_server import start_listener
from ecs_ec.consumption.reception import Reception
from ecs_ec.consumption.queries import Consumption
from ecs_ec.consumption.store import MeasurementStore


async def recovery_loop(service):
    """Recover durable work independently of sessions; expected transient failures retain pending003 state for retry."""
    while True:
        try:await service.recover()
        except asyncio.CancelledError:raise
        except Exception:
            service.signal(None,stage='observe',outcome='unexpected_error')
        await asyncio.sleep(1)


def acquisition_module(clock,settings=None):
    """Register optional acquisition ownership; disabled003 has no listener, worker or credentials prerequisite."""
    settings=settings or AcquisitionSettings()
    @asynccontextmanager
    async def lifespan(app):
        """Hold exclusive listener leadership, abort orphan writes and release every resource on shutdown."""
        if not settings.sftp_enabled:
            yield;return
        database=app.state.database
        async with database.engine.connect() as leader:
            lock=await leader.scalar(text('SELECT pg_try_advisory_lock(3003009)'))
            await leader.commit()
            if not lock:raise ValueError('acquisition_listener_already_active')
            listener=None;job=None
            try:
                async with database.sessions() as session:
                    rows=(await session.scalars(select(AcquisitionBinding).order_by(AcquisitionBinding.id,AcquisitionBinding.revision.desc()))).all()
                    latest={}
                    for row in rows:
                        if row.id not in latest:latest[row.id]=BindingInput.model_validate(row.data)
                    bindings=[row for row in latest.values() if row.enabled]
                if not bindings:raise ValueError('acquisition_binding_required')
                await abort_receiving(database,clock)
                processes={'process:acquisition:'+str(row.id):{row.building_id} for row in bindings}
                reception=Reception(database,clock,authorized_processes=processes)
                consumption=Consumption(database,clock,bindings[0].building_id,MeasurementStore())
                service=Acquisition(database,clock,settings,reception,consumption,getattr(app.state,'telemetry',None))
                app.state.acquisition=service
                listener=await start_listener(database,clock,settings,getattr(app.state,'telemetry',None))
                job=asyncio.create_task(recovery_loop(service),name='acquisition-recovery')
                yield
            finally:
                if listener:
                    listener.close();await listener.wait_closed()
                if job:
                    job.cancel()
                    with suppress(asyncio.CancelledError):await job
                await leader.execute(text('SELECT pg_advisory_unlock(3003009)'));await leader.commit()
    return Module('acquisition',lifespan=lifespan)
