"""Pure004 reproduction from preserved inputs, independent of today's supply/profile or002 original payloads."""

from ecs_ec.costs import engine
from ecs_ec.costs.money import digest
from ecs_ec.costs.schemas import InputEvidence
from ecs_ec.costs.repository import CostsProblem


def reproduce(snapshot, input_hash, engine_version):
    """Verify canonical captured hash/version and re-evaluate; unknown versions or tampering fail explicitly."""
    if engine_version != engine.ENGINE_VERSION:
        raise CostsProblem('engine_version_unavailable', 503)
    captured = InputEvidence.model_validate(snapshot).model_dump(mode='json')
    if digest(dict(engine_version=engine_version, inputs=captured)) != input_hash:
        raise CostsProblem('snapshot_hash_mismatch', 409)
    return engine.evaluate(InputEvidence.model_validate(captured))
