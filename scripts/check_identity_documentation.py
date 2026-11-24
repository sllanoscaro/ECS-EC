"""Check006 Python documentation without loading application secrets or connecting to PostgreSQL."""

import ast
from pathlib import Path


def main():
    """Review only006 source, security facade, CLI and its tests; fail with actionable source locations."""
    root = Path(__file__).resolve().parents[1]
    paths = [
        *root.glob("backend/src/ecs_ec/identity/*.py"),
        root / "backend/src/ecs_ec/core/security.py",
        root / "backend/src/ecs_ec/cli.py",
        *root.glob("backend/tests/contract/identity/*.py"),
        *root.glob("backend/tests/integration/identity/*.py"),
        *root.glob("backend/tests/unit/identity/*.py"),
        root / "scripts/seed_identity_reference.py",
        Path(__file__),
    ]
    missing = []
    for path in paths:
        tree = ast.parse(path.read_text(), filename=str(path))
        if not ast.get_docstring(tree):
            missing.append(f"{path.relative_to(root)}:1 module")
        for node in ast.walk(tree):
            if isinstance(
                node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ) and not ast.get_docstring(node):
                missing.append(f"{path.relative_to(root)}:{node.lineno} {node.name}")
    if missing:
        raise SystemExit("\n".join(missing))
    print(
        f"006 documentation: {len(paths)} Python files reviewed; no missing docstrings."
    )


if __name__ == "__main__":
    main()
