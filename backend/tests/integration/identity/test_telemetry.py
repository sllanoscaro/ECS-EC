"""006 technical signals use the actual007 emitter without retaining identity or credential values."""
import json
import pytest
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.observability.lifecycle import Telemetry, Policy

pytestmark = pytest.mark.integration


def drain(telemetry):
    """Collect validated actual007 bytes without network or a substitute emitter."""
    data=[]
    telemetry.logs._writer=data.append
    while telemetry.logs.drain_one():
        pass
    return [json.loads(item) for item in data]


async def test_login_authorization_mutation_recovery_signals(client, identity, account_factory, login, tmp_path, clock):
    """Correlate safe terminals for real login, permission rejection and recovery with no sensitive text."""
    telemetry=Telemetry(Policy(spool=tmp_path),clock=clock,autostart=False)
    client._transport.app.state.telemetry=telemetry
    account=await account_factory(role='administrador_tecnico')
    try:
        response=await login(account.email)
        assert response.status_code == 200
        current=await client.get('/api/v1/auth/session')
        assert current.status_code == 200
        initial=drain(telemetry)
        assert any(e['event']=='operation.completed' and e['operation']=='identity.authenticate' for e in initial)
        from ecs_ec.identity.telemetry import emission_scope
        with emission_scope(telemetry):
            await identity.recover_admin(account.email,'PRIVATE_RECOVERY_PASSWORD_006','PRIVATE_REASON_MARKER')
            with pytest.raises(IdentityProblem):
                identity.authorize(None,'identity.accounts.manage',identity.settings.building_id)
        events=initial+drain(telemetry)
        terminals=[e for e in events if e['event']=='operation.completed']
        assert any(e['operation']=='identity.authenticate' and e['outcome']=='success' for e in terminals)
        assert any(e['operation']=='administration.change' and e['outcome']=='success' for e in terminals)
        assert any(e['operation']=='identity.authorize' and e['outcome']=='expected_rejection' for e in terminals)
        assert all(e['operation_ref'] for e in terminals)
        encoded=json.dumps(events)
        for sensitive in (account.email,'Synthetic password 006','PRIVATE_RECOVERY','PRIVATE_REASON','127.0.0.1',response.cookies.get('ecs_ec_session','UNUSED_SECRET')):
            assert sensitive not in encoded
    finally:
        telemetry.shutdown()


@pytest.mark.parametrize('condition',['saturated','broken_emitter','broken_sink'])
async def test_mutation_and_authorization_survive_technical_failure(identity, account_factory, session_factory, tmp_path, clock, monkeypatch, condition):
    """Real account commits and policy remain available under queue saturation or actual007 IO/admission failures."""
    from ecs_ec.identity.telemetry import emission_scope
    from ecs_ec.identity.schemas import AccountCreate
    telemetry=Telemetry(Policy(spool=tmp_path),clock=clock,autostart=False)
    account=await account_factory(role='administrador_tecnico')
    _,principal=await session_factory(account)
    def fail(*args,**kwargs):
        """Inject a technical failure carrying a marker that must not cross telemetry or domain responses."""
        raise RuntimeError('PRIVATE_TECHNICAL_FAILURE')
    try:
        if condition=='saturated':
            for _ in range(1030):
                handle=telemetry.begin('identity.session','identity')
                telemetry.complete(handle)
        elif condition=='broken_emitter':
            monkeypatch.setattr(telemetry,'begin',fail)
        else:
            telemetry.logs._writer=fail
        with emission_scope(telemetry):
            identity.authorize(principal,'identity.accounts.manage',identity.settings.building_id)
            created=await identity.create_account(principal,AccountCreate(email='private-created@example.test',
                initial_password='PRIVATE_NEW_PASSWORD_006',role='operador',status='active'))
        assert created.role=='operador' and created.must_change_password
        if condition=='broken_sink':
            while telemetry.logs.drain_one():
                pass
            assert telemetry.logs.spool_dropped>0
        if condition=='saturated':
            assert telemetry.logs.dropped>0 and telemetry.logs.depth<=1024
        assert 'PRIVATE_NEW_PASSWORD' not in json.dumps(drain(telemetry))
    finally:
        telemetry.shutdown()


async def test_unexpected_hash_failure_is_safe_terminal(identity, account_factory, tmp_path, clock, monkeypatch):
    """Unexpected internal authentication failure is distinct from expected rejection and retains no exception text."""
    from ecs_ec.identity.telemetry import emission_scope
    telemetry=Telemetry(Policy(spool=tmp_path),clock=clock,autostart=False)
    account=await account_factory()
    async def fail(*args):
        """Abort hashing before a session or bucket commit, preserving a synthetic private marker."""
        raise RuntimeError('PRIVATE_HASH_FAILURE')
    monkeypatch.setattr(identity.credentials,'verify',fail)
    try:
        with emission_scope(telemetry), pytest.raises(RuntimeError):
            await identity.login(account.email,'PRIVATE_PASSWORD','PRIVATE_COOKIE','127.0.0.1')
        events=drain(telemetry)
        terminal=next(e for e in events if e['event']=='operation.completed' and e['operation']=='identity.authenticate')
        assert terminal['outcome']=='unexpected_error'
        assert 'PRIVATE_' not in json.dumps(events) and account.email not in json.dumps(events)
    finally:
        telemetry.shutdown()


async def test_concurrent_recoveries_keep_contexts_separate(identity, account_factory, tmp_path, clock):
    """Concurrent real service calls share an emitter but never their operation/stage references."""
    import asyncio
    from uuid import uuid4
    from ecs_ec.identity.telemetry import emission_scope
    accounts=[await account_factory(role='administrador_tecnico') for _ in range(2)]
    telemetry=Telemetry(Policy(spool=tmp_path),clock=clock,autostart=False)
    references=[uuid4(),uuid4()]
    async def recover(account,reference):
        """Recover exactly one fixture account within its own server-created technical context."""
        with emission_scope(telemetry,reference):
            await identity.recover_admin(account.email,'Synthetic recovery password006','Synthetic operational drill')
    try:
        await asyncio.gather(*(recover(account,reference) for account,reference in zip(accounts,references)))
        events=drain(telemetry)
        terminals=[e for e in events if e['event']=='operation.completed' and e['operation']=='administration.change']
        assert len(terminals)==2 and len({e['operation_ref'] for e in terminals})==2
        assert {e['parent_operation_ref'] for e in terminals}=={str(ref) for ref in references}
        for event in terminals:
            assert any(e['stage']=='commit' and e['operation_ref']==event['operation_ref'] for e in events)
    finally:
        telemetry.shutdown()
