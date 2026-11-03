"""003 configuration and versioned binding installation, limited to trusted deployment processes."""
import json
from pathlib import Path
from uuid import UUID
from pydantic import Field,SecretStr
from pydantic_settings import BaseSettings,SettingsConfigDict
from sqlalchemy import select
from ecs_ec.acquisition.schemas import BindingInput
from ecs_ec.acquisition.models import AcquisitionBinding,SftpSessionAttempt
from ecs_ec.acquisition.audit import append_audit
from ecs_ec.consumption.catalog_storage import BuildingRow,MeasurementSourceRow
from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork


class AcquisitionSettings(BaseSettings):
    """Private deployment options; disabled by default and never exported as functional configuration."""
    model_config=SettingsConfigDict(env_prefix='PAS600_',env_file='.env',extra='ignore',hide_input_in_errors=True)
    sftp_enabled:bool=False
    sftp_host:str='0.0.0.0'
    sftp_port:int=Field(default=2222,ge=0,le=65535)
    host_key_file:Path=Path('/run/secrets/pas600_host_key')
    auth_file:Path=Path('/run/secrets/pas600_auth.json')
    storage:Path=Path('/var/lib/ecs-ec/acquisition')
    maintenance_processes:str=''
    max_json_bytes:int=Field(default=256000,gt=0,le=256000)
    max_csv_bytes:int=Field(default=8*1024*1024,gt=0,le=8*1024*1024)
    max_session_bytes:int=Field(default=128*1024*1024,gt=0,le=128*1024*1024)
    max_files:int=Field(default=10000,gt=0,le=10000)

    def authorize(self,process):
        """Resolve maintenance authority from deployment configuration, never from a native publisher field."""
        if not process or process not in self.maintenance_processes.split(','):
            raise PermissionError('maintenance_not_authorized')

    def credentials(self):
        """Read bounded protected auth material; no values or paths enter reports or exception messages."""
        if not self.auth_file.is_file() or self.auth_file.stat().st_mode&0o077 or self.auth_file.stat().st_size>1048576:
            raise ValueError('protected_auth_required')
        return json.loads(self.auth_file.read_text())


async def install_binding(database,clock,settings,process,data):
    """Install a new immutable revision using existing001 sources; reject live-session or stale semantic replacement."""
    settings.authorize(process)
    binding=BindingInput.model_validate(data)
    async with UnitOfWork(database.sessions) as uow:
        await uow.session.scalar(select(BuildingRow).where(BuildingRow.id==binding.building_id).with_for_update())
        building=await uow.session.get(BuildingRow,binding.building_id)
        if building is None or building.timezone!=binding.timezone:raise ValueError('building_configuration_mismatch')
        active=await uow.session.scalar(select(SftpSessionAttempt.id).where(SftpSessionAttempt.binding_id==binding.id,SftpSessionAttempt.state=='receiving'))
        if active:raise ValueError('binding_in_use')
        previous=(await uow.session.scalars(select(AcquisitionBinding).where(AcquisitionBinding.id==binding.id).order_by(AcquisitionBinding.revision.desc()).limit(1))).first()
        if binding.revision!=(previous.revision+1 if previous else 1):raise ValueError('binding_revision_conflict')
        others=(await uow.session.scalars(select(AcquisitionBinding).where(AcquisitionBinding.username==binding.username,AcquisitionBinding.id!=binding.id))).all()
        if others:raise ValueError('identity_binding_conflict')
        for channel in binding.channels:
            source=await uow.session.get(MeasurementSourceRow,channel.source_id)
            if source is None or source.building_id!=binding.building_id:raise ValueError('unknown_source')
        row=AcquisitionBinding(id=binding.id,revision=binding.revision,building_id=binding.building_id,
            username=binding.username,enabled=binding.enabled,data=binding.model_dump(mode='json'),
            recorded_at=clock.now(),retain_until=anniversary(clock.now(),binding.timezone))
        uow.session.add(row)
        await append_audit(uow,clock,binding.timezone,'binding',binding.id)
        await uow.commit()
        return binding


async def current_binding(database,username):
    """Read the last trusted revision for one authenticated technical identity; stale enabled revisions grant nothing."""
    async with UnitOfWork(database.sessions) as uow:
        row=(await uow.session.scalars(select(AcquisitionBinding).where(AcquisitionBinding.username==username)
            .order_by(AcquisitionBinding.revision.desc()).limit(1))).first()
        if row is None or not row.enabled:return None
        return BindingInput.model_validate(row.data)
