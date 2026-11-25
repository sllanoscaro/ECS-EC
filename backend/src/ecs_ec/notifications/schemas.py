"""008 closed contract validation shared by input and immutable functional output.

contract.json is copied from specs/008-notificaciones-programables/contracts/openapi.json;
regenerate deliberately and keep the files byte-identical. Draft202012 checks all38
schemas, unions, extra fields and formats. Application checks add IANA and ordered
windows. Errors never contain input values, secrets or raw validator diagnostics.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker
from pydantic import RootModel, model_validator

from ecs_ec.core.timezones import iana_zone

CONTRACT = json.loads(Path(__file__).with_name("contract.json").read_text())


def instant(value):
    """Parse an explicit aware timestamp into UTC; reject local naive values."""
    value = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Aware timestamp required")
    return value.astimezone(UTC)


def validate(name, value):
    """Validate one named schema and domain invariants, returning its original typed JSON without coercion."""
    schema = {
        "$ref": "#/components/schemas/" + name,
        "components": CONTRACT["components"],
    }
    if not Draft202012Validator(schema, format_checker=FormatChecker()).is_valid(value):
        raise ValueError("notification_invalid_input")

    def check(node, allow_empty=False):
        """Validate nested windows and IANA names without transforming absent values into defaults."""
        if isinstance(node, dict):
            if "timezone" in node:
                try:
                    iana_zone(node["timezone"])
                except ZoneInfoNotFoundError:
                    raise ValueError("IANA timezone required") from None
            for path in node.get("protected_paths", []):
                if (
                    path.startswith("//")
                    or "\\" in path
                    or any(ord(c) < 32 or ord(c) == 127 for c in path)
                ):
                    raise ValueError("Protected local path required")
            if (
                "start" in node
                and "end" in node
                and (
                    instant(node["start"]) > instant(node["end"])
                    or (
                        instant(node["start"]) == instant(node["end"])
                        and not allow_empty
                    )
                )
            ):
                raise ValueError("Ordered window required")
            if (
                isinstance(node.get("window"), dict)
                and {"start", "end"} <= node["window"].keys()
                and node["window"]["start"] == node["window"]["end"]
                and node.get("initial_window_empty") is not True
            ):
                raise ValueError("Initial empty window must be explicit")
            if node.get("coverage") == "completa" and not node.get("covered_periods"):
                raise ValueError("History evidence required")
            for key, item in node.items():
                check(
                    item,
                    allow_empty=key == "window"
                    and node.get("initial_window_empty") is True
                    and (
                        node.get("type") == "resumen_periodico"
                        or "nominal_local" in node
                    ),
                )
        elif isinstance(node, list):
            for item in node:
                check(item)

    check(value)
    return value


class RuleInput(RootModel[dict]):
    """Periodic/urgent discriminated contract body; no caller actors, HTML or free recipient email."""

    @model_validator(mode="after")
    def checked(self):
        """Trim only the approved name then enforce the closed union, decimals, recipients and IANA zone."""
        body = dict(self.root)
        if isinstance(body.get("name"), str):
            body["name"] = body["name"].strip()
        if any(
            any(ord(c) < 32 or ord(c) == 127 for c in str(body.get(key, "")))
            for key in ["name"]
        ):
            raise ValueError("Invalid name")
        if isinstance(body.get("recipient_ids"), list):
            from uuid import UUID

            try:
                body["recipient_ids"] = [
                    str(UUID(value)) for value in body["recipient_ids"]
                ]
            except ValueError, TypeError, AttributeError:
                raise ValueError("Registered UUID recipient required") from None
        self.root = validate("RuleInput", body)
        return self
