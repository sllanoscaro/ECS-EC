"""003 integration fixtures use isolated PostgreSQL and actual001 bootstrap/002 admission."""
from pathlib import Path
from uuid import UUID
import pytest
from sqlalchemy import text
from ecs_ec.acquisition.config import AcquisitionSettings,install_binding


@pytest.fixture
async def acquisition_environment(history_environment,database,clock,tmp_path):
    """Install a trusted synthetic binding over existing001 sources; never inject native or accepted records."""
    async with database.engine.begin() as connection:
        await connection.execute(text('TRUNCATE acquisition_binding CASCADE'))
    settings=AcquisitionSettings(_env_file=None,storage=tmp_path/'bytes',maintenance_processes='process:test',sftp_host='127.0.0.1',sftp_port=0)
    channels=[dict(source_id=str(UUID(int=i)),category_id=f'CAT-{i:02}',device_local_id=f'modbus:1_mb_{i}',
        reduced_id=f'{i}_mb',device_name=f'iEM3150 CAT{i:02}',csv_topic_id=f'modbus:1_mb_EaImport{i}',json_value_item_id=f'modbus:1_mb_EaImport{i}') for i in range(1,8)]
    binding=await install_binding(database,clock,settings,'process:test',dict(id=str(UUID(int=3003)),revision=1,
        building_id=str(UUID(int=99)),username='pas600',publisher_serial='SIMULATED-PAS600-001',
        publisher_remote_id='urn:dev:cer:1111111111111111111111111111111111111111',timezone='America/Santiago',channels=channels))
    try:
        yield dict(database=database,clock=clock,settings=settings,binding=binding,reception=history_environment)
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text('TRUNCATE acquisition_binding CASCADE'))


@pytest.fixture
async def sftp_environment(acquisition_environment,tmp_path):
    """Start the real listener with managed host key, public-key/password modes and no human identity dependency."""
    import asyncssh,json
    from argon2 import PasswordHasher
    from ecs_ec.acquisition.sftp_server import start_listener
    env=dict(acquisition_environment)
    host=tmp_path/'host';hostkey=asyncssh.generate_private_key('ssh-ed25519');hostkey.write_private_key(host);host.chmod(0o600)
    private=tmp_path/'client';clientkey=asyncssh.generate_private_key('ssh-ed25519');clientkey.write_private_key(private);private.chmod(0o600)
    auth=tmp_path/'auth';auth.write_text(json.dumps({'pas600':{'password_hash':PasswordHasher().hash('Synthetic password003'),'public_keys':[clientkey.export_public_key().decode()]}}));auth.chmod(0o600)
    settings=env['settings'].model_copy(update={'host_key_file':host,'auth_file':auth})
    listener=await start_listener(env['database'],env['clock'],settings)
    known=tmp_path/'known';known.write_bytes(f'[127.0.0.1]:{listener.get_port()} '.encode()+hostkey.export_public_key())
    env.update(listener=listener,known=known,private=private,port=listener.get_port())
    try:yield env
    finally:listener.close();await listener.wait_closed()
