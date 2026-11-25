"""Render the versioned technical dashboards for one explicit external deployment policy.

Inputs: trusted environment/revision/sampling and an external output directory. Output:
atomic private platform.json/notifications.json files for Compose's read-only OBS_DASHBOARD_DIRECTORY mount.
No credentials, business data, network calls or persistent feature selection are used.
The repository dashboard remains the canonical source; rerun this script to regenerate.
"""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path


def render(environment, revision, ratio, output):
    """Validate the same policy as the emitter, then atomically render its known installed dashboards."""
    from ecs_ec.observability.lifecycle import Policy

    repo = Path(__file__).resolve().parents[2]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", revision):
        raise ValueError("Invalid policy revision")
    policy = Policy(
        environment=environment,
        revision=revision,
        trace_ratio=ratio,
        retention_hours=24 if environment == "test" else 168,
        spool=output / "unused-spool",
    )
    if (
        not output.is_absolute()
        or output.resolve().is_relative_to(repo)
        or any(parent.is_symlink() for parent in (output, *output.parents))
    ):
        raise ValueError("Choose an external absolute directory")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.stat().st_uid != os.getuid() or output.stat().st_mode & 0o077:
        raise ValueError("Private owned output directory required")
    sources = [
        repo / "deploy/observability/grafana/dashboards" / name
        for name in ("platform.json", "notifications.json")
    ]
    sources = [source for source in sources if source.is_file()]
    if any((output / source.name).is_symlink() for source in sources):
        raise ValueError("Unsafe output")
    for source in sources:
        destination = output / source.name
        dashboard = json.loads(source.read_text())
        dashboard["description"] = (
            "Generated from canonical repository dashboards; regenerate for each external deployment policy."
        )
        for variable in dashboard["templating"]["list"]:
            if variable["name"] == "environment":
                variable["current"] = {"text": environment, "value": environment}
        for panel in dashboard["panels"]:
            if panel["type"] == "ecsec-coverage-panel":
                panel["options"].update(
                    revision=policy.revision, traceRatio=policy.trace_ratio
                )
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", dir=output, prefix="." + source.stem + "-", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(dashboard, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(0o600)
            temporary.replace(destination)
        finally:
            if temporary and temporary.exists():
                temporary.unlink()
    return output / "platform.json"


def main():
    """Accept no secret options; return a fixed failure reason and only the public output path on success."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environment", choices=["local", "test", "vps"], required=True
    )
    parser.add_argument("--policy-revision", required=True)
    parser.add_argument("--trace-ratio", type=float, choices=[1.0, 0.1], default=1.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(
            render(
                args.environment, args.policy_revision, args.trace_ratio, args.output
            )
        )
    except ValueError, OSError:
        parser.exit(
            1,
            "Dashboard policy rendering failed; verify policy and private external paths.\n",
        )


if __name__ == "__main__":
    main()
