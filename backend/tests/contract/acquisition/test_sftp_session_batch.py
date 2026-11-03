"""Real SSH/SFTP channel events are the publication boundary; byte completeness is never inferred."""
import asyncio
import pytest
import asyncssh
from sqlalchemy import select
from ecs_ec.acquisition.models import SftpSessionAttempt,NativePublication
from ecs_ec.core.unit_of_work import UnitOfWork
from backend.tests.integration.acquisition.conftest import acquisition_environment,sftp_environment

pytestmark=pytest.mark.integration


async def test_explicit_close_then_clean_eof_seals(acquisition_environment,tmp_path):
    """A managed host key and protocol CLOSE/CHANNEL_EOF seal; dropping SSH after CLOSE never seals."""
    from ecs_ec.acquisition.sftp_server import start_listener
    import json
    from argon2 import PasswordHasher
    env=acquisition_environment
    key=asyncssh.generate_private_key('ssh-ed25519')
    host=tmp_path/'host';key.write_private_key(host);host.chmod(0o600)
    auth=tmp_path/'auth';auth.write_text(json.dumps({'pas600':{'password_hash':PasswordHasher().hash('Synthetic password003')}}));auth.chmod(0o600)
    settings=env['settings'].model_copy(update={'host_key_file':host,'auth_file':auth})
    server=await start_listener(env['database'],env['clock'],settings)
    port=server.get_port()
    known=tmp_path/'known_hosts';known.write_bytes(f'[127.0.0.1]:{port} '.encode()+key.export_public_key())
    name='20260101003000000_1.json'
    try:
        connection=await asyncssh.connect('127.0.0.1',port,username='pas600',password='Synthetic password003',known_hosts=str(known))
        sftp=await connection.start_sftp_client()
        async with sftp.open(name,'xb') as stream:await stream.write(b'{}')
        connection.abort()
        await connection.wait_closed()
        await asyncio.sleep(.1)
        async with UnitOfWork(env['database'].sessions) as uow:
            assert not (await uow.session.scalars(select(NativePublication))).all()
        connection=await asyncssh.connect('127.0.0.1',port,username='pas600',password='Synthetic password003',known_hosts=str(known))
        sftp=await connection.start_sftp_client()
        async with sftp.open(name,'xb') as stream:await stream.write(b'{}')
        sftp.exit();await sftp.wait_closed()
        connection.close();await connection.wait_closed()
        async with UnitOfWork(env['database'].sessions) as uow:
            rows=(await uow.session.scalars(select(SftpSessionAttempt).order_by(SftpSessionAttempt.recorded_at,SftpSessionAttempt.id))).all()
            assert sorted(r.state for r in rows)==['aborted','sealed']
            assert len((await uow.session.scalars(select(NativePublication))).all())==1
    finally:
        server.close();await server.wait_closed()


async def test_public_key_host_verification_shell_and_probe(sftp_environment,tmp_path):
    """Key auth is technical-only; unknown host fails, shell denial consumes no receiving slot, and probe creates no publication."""
    env=sftp_environment
    other=asyncssh.generate_private_key('ssh-ed25519')
    wrong=tmp_path/'wrong';wrong.write_bytes(f'[127.0.0.1]:{env["port"]} '.encode()+other.export_public_key())
    with pytest.raises(asyncssh.HostKeyNotVerifiable):
        await asyncssh.connect('127.0.0.1',env['port'],username='pas600',client_keys=[str(env['private'])],known_hosts=str(wrong))
    async with asyncssh.connect('127.0.0.1',env['port'],username='pas600',client_keys=[str(env['private'])],known_hosts=str(env['known'])) as connection:
        for _ in range(3):
            with pytest.raises(asyncssh.ChannelOpenError):await connection.run('id')
        sftp=await connection.start_sftp_client()
        async with sftp.open('.ecs-ec-probe','xb') as stream:await stream.write(b'probe')
        await sftp.remove('.ecs-ec-probe')
        sftp.exit();await sftp.wait_closed()
    async with UnitOfWork(env['database'].sessions) as uow:
        assert not (await uow.session.scalars(select(NativePublication))).all()
        rows=(await uow.session.scalars(select(SftpSessionAttempt))).all()
        assert len(rows)==1 and rows[0].reason=='empty_or_probe'


async def test_clean_eof_with_pending_handle_aborts(sftp_environment):
    """Even explicit EOF cannot substitute for the client's missing CLOSE; implicit library cleanup never seals."""
    env=sftp_environment
    async with asyncssh.connect('127.0.0.1',env['port'],username='pas600',client_keys=[str(env['private'])],known_hosts=str(env['known'])) as connection:
        sftp=await connection.start_sftp_client()
        stream=await sftp.open('20260101003000000_1.json','xb');await stream.write('{}')
        sftp.exit();await sftp.wait_closed()
    async with UnitOfWork(env['database'].sessions) as uow:
        rows=(await uow.session.scalars(select(SftpSessionAttempt))).all()
        assert len(rows)==1 and rows[0].state=='aborted'
        assert not (await uow.session.scalars(select(NativePublication))).all()
