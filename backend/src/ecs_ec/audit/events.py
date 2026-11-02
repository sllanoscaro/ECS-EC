"""Typed producer envelopes and atomic PostgreSQL event append/deduplication."""

import json
import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from jsonschema import Draft202012Validator
from pydantic import AfterValidator, AliasChoices, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ecs_ec.audit.models import FunctionalEvent
from ecs_ec.core.clock import Clock, utc
from ecs_ec.core.errors import InvalidEvidence
from ecs_ec.core.retention import anniversary
from ecs_ec.core.unit_of_work import UnitOfWork

UTCInstant = Annotated[AwareDatetime, AfterValidator(utc)]
Code = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_.:-]{0,99}$", max_length=100)]
OpaqueRef = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:/-]{1,200}$", max_length=200)]
Revision = Annotated[int, Field(gt=0, le=2147483647, strict=True)]


class EvidenceInput(BaseModel):
    """Immutable typed envelopes; writers revalidate copies to prevent model_construct bypasses."""

    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class Interval(EvidenceInput):
    """An aware half-open interval, normalized to UTC; equal/reversed endpoints are invalid."""

    start: UTCInstant
    end: UTCInstant

    @model_validator(mode="after")
    def ordered(self):
        """Require strictly increasing endpoints before serialization or persistence."""
        if self.start >= self.end:
            raise ValueError("Interval start must precede end")
        return self


class SafePayload(BaseModel):
    """Producer schemas inherit this strict allowlist base; no arbitrary/free-text bodies.

    Use codes with bounded patterns, Literal vocabularies, UUIDs, aware timestamps and
    typed numeric fields. Registration is a trusted composition step, never an API.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)


def _check_schema(node):
    """Require closed objects and constrained strings recursively, including referenced definitions."""
    if isinstance(node, dict):
        if node.get("type") == "object" and node.get("additionalProperties") is not False:
            raise ValueError("Payload objects must forbid additional properties")
        if node.get("type") == "string" and not (
            "enum" in node or "const" in node or node.get("format") in {"uuid", "date-time", "date"}
            or ("pattern" in node and "maxLength" in node)
        ):
            raise ValueError("Payload strings require a bounded code pattern or explicit vocabulary")
        for child in node.values():
            _check_schema(child)
    elif isinstance(node, list):
        for child in node:
            _check_schema(child)


def _check_safe_values(node):
    """Reject secret/body/SQL field names and control characters even in registered payloads."""
    if isinstance(node, dict):
        for key, value in node.items():
            normalized = re.sub(r"[^a-z]", "", key.lower())
            if any(word in normalized for word in (
                "password", "secret", "token", "authorization", "cookie", "sql", "exception",
                "traceback", "body", "email", "credentials",
            )):
                raise ValueError("Unsafe payload field")
            _check_safe_values(value)
    elif isinstance(node, list):
        for value in node:
            _check_safe_values(value)
    elif isinstance(node, str) and any(ord(char) < 32 or ord(char) == 127 for char in node):
        raise ValueError("Control characters are not allowed")


class PayloadRegistry:
    """Closed producer-owned action/type schemas, independent of all consumers."""

    def __init__(self):
        """Create an empty registry; absent business modules imply no approved business payloads."""
        self._schemas: dict[str, tuple[type[SafePayload], Draft202012Validator, frozenset[str]]] = {}

    def register(self, code: str, model: type[SafePayload], *, results=()) -> None:
        """Register an immutable schema and explicit audit result vocabulary; reject unsafe definitions."""
        if code in self._schemas or not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,99}", code):
            raise ValueError("Invalid or duplicate schema registration")
        if not issubclass(model, SafePayload):
            raise ValueError("Producer schema must inherit SafePayload")
        schema = model.model_json_schema()
        _check_schema(schema)
        Draft202012Validator.check_schema(schema)
        results = frozenset(results)
        if any(not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,99}", result) for result in results):
            raise ValueError("Audit results must be safe stable codes")
        self._schemas[code] = (model, Draft202012Validator(schema), frozenset(results))

    def validate(self, code: str, payload: dict, result: str | None = None) -> dict:
        """Validate strict typed JSON, allowlisted results and sanitation; raise only safe errors."""
        try:
            model, validator, results = self._schemas[code]
            if result is not None and result not in results:
                raise ValueError("Unregistered result")
            safe = model.model_validate(payload).model_dump(mode="json")
            validator.validate(safe)
            _check_safe_values(safe)
            if len(json.dumps(safe, allow_nan=False).encode()) > 16_384:
                raise ValueError("Evidence payload exceeds 16 KiB")
            return safe
        except Exception:
            raise InvalidEvidence() from None


class EventInput(EvidenceInput):
    """Trusted event envelope: event_id→id, event_type→event_type, measurement_window→effective_window.

    Optional category_id and functional_result belong to the producer's approved payload
    schema. recorded_at and retain_until are supplied by the writer's internal clock.
    """

    event_id: UUID
    event_type: Code = Field(validation_alias=AliasChoices("type", "event_type"), serialization_alias="type")
    source_module: Code
    source_entity_id: UUID
    source_revision: Revision
    occurred_at: UTCInstant
    measurement_window: Interval | None = None
    accepted_new_data: bool = Field(default=False, strict=True)
    safe_payload: dict
    correlation_ref: OpaqueRef | None = None


class EventWriter:
    """Append functional events in the producer's UoW without commit, SMTP, broker or telemetry."""

    def __init__(self, schemas: PayloadRegistry, clock: Clock, timezone: str):
        """Receive trusted schemas, internal time and the building IANA retention zone."""
        self.schemas, self.clock, self.timezone = schemas, clock, timezone

    async def append(self, uow: UnitOfWork, event: EventInput) -> FunctionalEvent:
        """Insert once per provenance and return the original row on conflict, including concurrent retries.

        PostgreSQL READ COMMITTED arbitrates uniqueness. Reusing a primary UUID for another
        provenance is an error. A failed producer must roll back and use a new UoW for
        its failure result/event. Database failures propagate; durability is never assumed.
        """
        try:
            event = EventInput.model_validate(event.model_dump())
        except Exception:
            raise InvalidEvidence() from None
        payload = self.schemas.validate(event.event_type, event.safe_payload)
        now = utc(self.clock.now())
        statement = insert(FunctionalEvent).values(
            id=event.event_id, event_type=event.event_type, source_module=event.source_module,
            source_entity_id=event.source_entity_id, source_revision=event.source_revision,
            occurred_at=event.occurred_at, recorded_at=now,
            effective_window=event.measurement_window.model_dump(mode="json") if event.measurement_window else None,
            accepted_new_data=event.accepted_new_data, safe_payload=payload,
            correlation_ref=event.correlation_ref, retain_until=anniversary(now, self.timezone),
        ).on_conflict_do_nothing(constraint="uq_event_provenance").returning(FunctionalEvent)
        row = (await uow.session.scalars(statement)).one_or_none()
        if row is None:
            row = (await uow.session.scalars(select(FunctionalEvent).where(
                FunctionalEvent.source_module == event.source_module,
                FunctionalEvent.source_entity_id == event.source_entity_id,
                FunctionalEvent.source_revision == event.source_revision,
                FunctionalEvent.event_type == event.event_type,
            ))).one()
        return row
