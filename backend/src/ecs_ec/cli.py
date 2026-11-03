"""Host-only identity bootstrap/recovery commands; passwords are read twice from a non-echoing TTY."""

import argparse
import asyncio
import getpass
import sys

from pydantic import ValidationError

from ecs_ec.core.clock import SystemClock
from ecs_ec.core.database import Database
from ecs_ec.core.settings import Settings
from ecs_ec.identity.credentials import valid_password
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.services import Identity


class SafeParser(argparse.ArgumentParser):
    """Do not echo unknown arguments that could accidentally contain a password."""

    def error(self, message):
        """Return a fixed argument error instead of reflecting arbitrary command-line values."""
        self.exit(2, "Argumentos no admitidos. Consulte --help.\n")


def read_password():
    """Require an interactive protected TTY and matching exact Unicode inputs, without echo or logs."""
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise IdentityProblem("invalid_input", 422)
    first = getpass.getpass("Nueva contraseña: ")
    second = getpass.getpass("Confirmar nueva contraseña: ")
    if first != second:
        raise IdentityProblem("invalid_input", 422)
    return valid_password(first)


async def execute(options, password):
    """Run the same guarded service as HTTP and release DB resources even after failure."""
    settings = Settings()
    database = Database(settings.database_url.get_secret_value())
    identity = Identity(database, settings.identity_options(), SystemClock(), settings.building_timezone)
    from ecs_ec.identity.telemetry import emission_scope
    from ecs_ec.observability.lifecycle import Telemetry
    telemetry = Telemetry.from_environment(clock=identity.clock)
    try:
        with emission_scope(telemetry):
            await execute_identity_command(identity, options, password)
    finally:
        telemetry.shutdown()
        await database.close()


async def execute_identity_command(identity, options, password):
    """Dispatch the guarded service within the host's technical context; never inspect credential values."""
    if options.command == "bootstrap-admin":
        await identity.bootstrap(options.email, password)
    else:
        await identity.recover_admin(options.email, password, options.reason)


def main(argv=None):
    """Parse host-only commands and emit a fixed success/failure, never hashes, email or entered secrets."""
    parser = SafeParser(prog="ecs-ec")
    groups = parser.add_subparsers(dest="group", required=True)
    identity = groups.add_parser("identity")
    commands = identity.add_subparsers(dest="command", required=True)
    for name in ("bootstrap-admin", "recover-admin"):
        command = commands.add_parser(name)
        command.add_argument("--email", required=True)
        if name == "recover-admin":
            command.add_argument("--reason", required=True)
    options = parser.parse_args(argv)
    try:
        password = read_password()
        asyncio.run(execute(options, password))
    except IdentityProblem as problem:
        print(problem.detail, file=sys.stderr)
        return 1
    except (ValidationError, Exception):
        print("No se pudo confirmar la operación. Revise configuración y estado antes de repetirla.", file=sys.stderr)
        return 1
    print("Operación confirmada. El titular debe renovar la contraseña al ingresar.")
    return 0
