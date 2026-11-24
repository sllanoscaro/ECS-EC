"""002:T064 consumer acceptance over real003 generation, SFTP and durable002 receipt.

Synthetic descriptors do not certify DOCA0172EN-19 or physical firmware. Faults are
injected only at the003→002 call boundary; actual commits/reads use PostgreSQL18.
Functional900s boundaries use FrozenClock and are not sender real-time measurements.
"""

import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import asyncssh
import pytest
from sqlalchemy import select

from backend.tests.integration.acquisition.conftest import acquisition_environment, sftp_environment  # noqa: F401
from backend.tests.integration.acquisition.test_recovery import native_bytes, service
from backend.tests.support.source_sftp import evaluations, generated_publication, publish_generated, send_native
from ecs_ec.acquisition.models import PublicationEvaluation
from ecs_ec.acquisition.store import digest
from ecs_ec.consumption.models import CategoryUpdate, IncorporatedRecord, ReceptionAttempt, instant
from ecs_ec.core.unit_of_work import UnitOfWork

pytestmark = pytest.mark.integration
NAME = "20260101003000000_1.json"


async def incorporated(env):
    """Read only physical002 evidence in chronological order; calculated totals cannot mask duplicates."""
    async with UnitOfWork(env["database"].sessions) as uow:
        rows = (await uow.session.scalars(select(IncorporatedRecord).where(
            IncorporatedRecord.kind == "measured",
        ).order_by(IncorporatedRecord.start))).all()
        # Keep loaded immutable observations usable after the caller's readonly rollback.
        uow.session.expunge_all()
        return rows


@pytest.mark.parametrize("native_format", ["csv", "json"])
async def test_real_simulator_publication_preserves_receipt_identity(sftp_environment, tmp_path, native_format):
    """The installed003 generator/publisher delivers two4kWh intervals in one002 category update."""
    env = sftp_environment
    run = await generated_publication(env, tmp_path, native_format)
    await publish_generated(env, tmp_path, run)
    assert len(await evaluations(env)) == 1
    await service(env).recover()
    evaluation, = await evaluations(env)
    rows = await incorporated(env)
    assert evaluation.state == "completed" and evaluation.input_digest == digest(evaluation.input_records)
    assert [result["status"] for result in evaluation.outcome["results"]] == ["accepted", "accepted"]
    assert len(evaluation.outcome["updates"]) == 1
    assert evaluation.outcome["updates"][0]["accepted_count"] == 2
    assert [row.energy_kwh for row in rows] == [Decimal("4"), Decimal("4")]
    assert {row.source_id for row in rows} == {UUID(int=3)}
    assert {row.category_id for row in rows} == {"CAT-03"}
    assert [(row.start, row.end) for row in rows] == [
        (instant("2026-01-01T00:00:00Z"), instant("2026-01-01T00:15:00Z")),
        (instant("2026-01-01T00:15:00Z"), instant("2026-01-01T00:30:00Z")),
    ]
    assert len({row.update_id for row in rows}) == 1
    assert all(row.source_evidence_ref.startswith("acquisition:") for row in rows)
    assert {row.id for row in rows} == {UUID(result["measurement_id"]) for result in evaluation.outcome["results"]}


async def test_fragments_wait_for_clean_eof_and_form_one_update(sftp_environment):
    """Closed files plus a still-open last file cannot admit a prefix; EOF yields both adjacent deltas together."""
    env = sftp_environment
    later = json.loads(native_bytes())
    later["message"]["content"]["data"]["timeseries"][0]["records"] = [{"v": 109, "t": 1800000}]
    async with asyncssh.connect(
        "127.0.0.1", env["port"], username="pas600", client_keys=[str(env["private"])],
        known_hosts=str(env["known"]),
    ) as connection:
        sftp = await connection.start_sftp_client()
        async with sftp.open(NAME, "xb", encoding=None) as stream:
            await stream.write(native_bytes())
        async with sftp.open("20260101003000000_2.json", "xb", encoding=None) as stream:
            await stream.write(json.dumps(later).encode())
            assert await service(env).recover() == 0
            assert await evaluations(env) == [] and await incorporated(env) == []
        assert await service(env).recover() == 0  # All CLOSEs alone are not a publication commit.
        sftp.exit()
        await sftp.wait_closed()
    await service(env).recover()
    evaluation, = await evaluations(env)
    assert [row.energy_kwh for row in await incorporated(env)] == [Decimal("4"), Decimal("5")]
    assert len(evaluation.outcome["updates"]) == 1
    assert evaluation.outcome["updates"][0]["accepted_count"] == 2


@pytest.mark.parametrize("boundary", ["before_receipt", "lost_committed_response"])
async def test_restart_recovers_persisted_id_and_input(sftp_environment, monkeypatch, boundary):
    """Before002 begins,003 has committed ID/input; restart resumes that ID or reads its original committed outcome."""
    env = sftp_environment
    await send_native(env, [(NAME, native_bytes())])
    acquisition = service(env)
    actual_accept = acquisition.reception.accept
    frozen = {}

    async def interrupted(*arguments):
        """Inspect durable003 state before the real002 call, then inject the selected process boundary."""
        evaluation, = await evaluations(env)
        assert evaluation.attempt_id == arguments[0] and evaluation.input_records == arguments[4]
        assert evaluation.input_digest == digest(arguments[4])
        frozen.update(attempt=evaluation.attempt_id, records=evaluation.input_records)
        async with UnitOfWork(env["database"].sessions) as uow:
            assert await uow.session.get(ReceptionAttempt, evaluation.attempt_id) is None
        if boundary == "lost_committed_response":
            frozen["outcome"] = (await actual_accept(*arguments)).model_dump(mode="json")
        raise RuntimeError("synthetic_process_interruption")

    monkeypatch.setattr(acquisition.reception, "accept", interrupted)
    with pytest.raises(RuntimeError, match="synthetic_process_interruption"):
        await acquisition.recover()
    restarted = service(env)
    actual_lookup = restarted.reception.read_attempt
    observed = []

    async def lookup(*arguments):
        """Observe the real002 recovery lookup; never replace its state or outcome."""
        observed.append(arguments[0])
        return await actual_lookup(*arguments)

    monkeypatch.setattr(restarted.reception, "read_attempt", lookup)
    if boundary == "lost_committed_response":
        async def forbidden_accept(*arguments):
            """A completed lookup must avoid reprocessing entirely, including a redundant accept call."""
            pytest.fail("completed_attempt_reprocessed")
        monkeypatch.setattr(restarted.reception, "accept", forbidden_accept)
    await restarted.recover()
    evaluation, = await evaluations(env)
    assert observed == [frozen["attempt"]]
    assert evaluation.attempt_id == frozen["attempt"] and evaluation.input_records == frozen["records"]
    assert evaluation.state == "completed" and len(await incorporated(env)) == 1
    if "outcome" in frozen:
        assert evaluation.outcome == frozen["outcome"]
    before = [(row.id, row.first_incorporated_at, row.retain_until) for row in await incorporated(env)]
    assert await restarted.recover() == 0
    assert [(row.id, row.first_incorporated_at, row.retain_until) for row in await incorporated(env)] == before


async def test_too_early_requires_new_attempt_at_next_admissible(sftp_environment):
    """A confirmed899s rejection stays immutable at900s; explicit SFTP resend admits the pending5kWh with a new ID."""
    env = sftp_environment
    await send_native(env, [(NAME, native_bytes())])
    await service(env).recover()
    first, = await evaluations(env)
    next_time = env["clock"].now() + timedelta(seconds=900)
    extended = json.loads(native_bytes())
    extended["message"]["content"]["data"]["timeseries"][0]["records"].append({"v": 109, "t": 1800000})
    payload = json.dumps(extended).encode()
    env["clock"].advance(899)
    await send_native(env, [(NAME, payload)])
    await service(env).recover()
    rejected = next(row for row in await evaluations(env) if row.id != first.id)
    assert [r["status"] for r in rejected.outcome["results"]] == ["duplicate", "rejected"]
    assert rejected.outcome["results"][1]["reason_code"] == "too_early"
    assert instant(rejected.outcome["updates"][0]["next_admissible_at"]) == next_time
    env["clock"].advance(1)
    acquisition = service(env)
    assert await acquisition.recover() == 0 and len(await incorporated(env)) == 1
    lookup = await acquisition.reception.read_attempt(
        rejected.attempt_id, env["binding"].building_id, "process:acquisition:" + str(env["binding"].id),
    )
    assert lookup.outcome.model_dump(mode="json") == rejected.outcome
    await send_native(env, [(NAME, payload)])
    await acquisition.recover()
    resent = next(row for row in await evaluations(env) if row.id not in {first.id, rejected.id})
    assert resent.publication_id == rejected.publication_id and resent.attempt_id != rejected.attempt_id
    assert [r["status"] for r in resent.outcome["results"]] == ["duplicate", "accepted"]
    assert [row.energy_kwh for row in await incorporated(env)] == [Decimal("4"), Decimal("5")]
    async with UnitOfWork(env["database"].sessions) as uow:
        original = await uow.session.get(PublicationEvaluation, rejected.id)
        assert original.outcome == rejected.outcome
        updates = (await uow.session.scalars(select(CategoryUpdate).where(CategoryUpdate.category_id == "CAT-03"))).all()
        assert sorted(row.accepted_count for row in updates) == [0, 1, 1]
