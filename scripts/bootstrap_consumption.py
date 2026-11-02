"""Trusted local001 context/initial-source provisioning; no public seed or account management.

DATABASE_URL is read using existing platform Settings. Context/source JSON files contain
only installation metadata. Only first configuration/no-op may run before002 is installed.
Run `uv run --locked python scripts/bootstrap_consumption.py --help` for arguments.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from ecs_ec.consumption.bootstrap import bootstrap
from ecs_ec.consumption.configuration import ConfigurationError
from ecs_ec.consumption.models import BuildingContext, ConfigurationInput
from ecs_ec.core.clock import SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.settings import Settings
from ecs_ec.core.unit_of_work import UnitOfWork


async def provision(context_file: Path, configuration_file: Path):
    """Validate both files before DB access, then commit configuration/audit/events together or roll back."""
    clock = SystemClock()
    context = BuildingContext.model_validate(json.loads(context_file.read_text()) | {"created_at": clock.now()})
    configuration = ConfigurationInput.model_validate_json(configuration_file.read_text())
    database = Database(Settings().database_url.get_secret_value())
    try:
        async with UnitOfWork(database.sessions) as uow:
            revision = await bootstrap(uow, building=context, configuration=configuration, clock=clock,
                actor_ref="process:consumption_bootstrap")
            await uow.commit()
            return revision.revision
    finally: await database.close()


def main():
    """Parse local file paths and print only a safe status/code, never source inputs or DB credentials."""
    parser = argparse.ArgumentParser(description="Preparar contexto y primera configuración de consumo001.")
    parser.add_argument("--context-file", type=Path, required=True, help="JSON con id, name y timezone explícitos.")
    parser.add_argument("--configuration-file", type=Path, required=True, help="ConfigurationInput completo de spec-001.")
    args = parser.parse_args()
    try: revision = asyncio.run(provision(args.context_file, args.configuration_file))
    except ConfigurationError as error:
        print(error.code, file=sys.stderr)
        return 1
    except Exception:
        print("consumption_bootstrap_failed", file=sys.stderr)
        return 1
    print(f"Configuración de consumo preparada: revisión {revision}.")
    return 0


if __name__ == "__main__": raise SystemExit(main())
