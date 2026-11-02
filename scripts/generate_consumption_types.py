"""Generate readonly TypeScript wire shapes from001 OpenAPI; constraints remain server-validated.

Run `uv run --locked python scripts/generate_consumption_types.py` from the repository
root. JSON Schema ranges, uniqueness and conditional invariants are intentionally not
pretended to be runtime TypeScript checks. No external generator/dependency is required.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "specs/001-visualizar-consumo-categorias/contracts/openapi.json"
TARGET = ROOT / "frontend/src/lib/api/consumption-types.ts"


def wire_type(schema):
    """Map OpenAPI refs, unions, primitive literals and required properties to readonly TS shapes."""
    if "$ref" in schema: return schema["$ref"].rsplit("/", 1)[1]
    if "const" in schema: return json.dumps(schema["const"], ensure_ascii=False)
    if "enum" in schema: return " | ".join(json.dumps(v, ensure_ascii=False) for v in schema["enum"])
    for union in ("oneOf", "anyOf"):
        if union in schema: return "(" + " | ".join(wire_type(s) for s in schema[union]) + ")"
    kind = schema.get("type")
    if kind == "array": return f"ReadonlyArray<{wire_type(schema['items'])}>"
    if kind == "object":
        required = schema.get("required", [])
        return "{ " + " ".join(f"readonly {name}{'' if name in required else '?'}: {wire_type(value)};"
            for name, value in schema["properties"].items()) + " }"
    try: return {"string": "string", "integer": "number", "number": "number", "boolean": "boolean", "null": "null"}[kind]
    except KeyError: raise ValueError(f"Unsupported wire shape: {kind}") from None


def render():
    """Return deterministic documented declarations; energy/date-time values remain textual strings."""
    schemas = json.loads(SOURCE.read_text())["components"]["schemas"]
    lines = ["/** Generated from spec-001 OpenAPI by scripts/generate_consumption_types.py; do not edit. */"]
    for name, schema in schemas.items():
        lines.extend([f"/** Wire shape of OpenAPI {name}; semantic constraints are checked by the server. */",
                      f"export type {name} = {wire_type(schema)};"])
    return "\n".join(lines) + "\n"


def main():
    """Regenerate only the consumption wire declarations in the existing frontend source tree."""
    TARGET.write_text(render())


if __name__ == "__main__": main()
