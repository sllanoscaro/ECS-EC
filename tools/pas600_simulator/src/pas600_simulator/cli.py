"""Standalone CLI; validate without filesystem writes, network or backend imports."""
import argparse
import json
import sys
from pathlib import Path
from pydantic import ValidationError
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.identity import scenario_hashes


class SafeParser(argparse.ArgumentParser):
    """Arguments are not a credential channel; reject malformed input without echoing arbitrary command values."""
    def error(self,message):
        """Return a fixed configuration diagnostic instead of argparse's potentially secret argument transcript."""
        self.exit(2,'Invalid arguments. Use --help for supported options.\n')


def main() -> int:
    """Validate or generate a strict scenario; return 0, configuration 2 or evidence 5."""
    parser = SafeParser(prog='pas600-sim')
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate')
    validate.add_argument('--scenario', type=Path, required=True)
    generate = commands.add_parser('generate')
    generate.add_argument('--scenario', type=Path, required=True)
    generate.add_argument('--output', type=Path, required=True)
    generate.add_argument('--format', choices=['csv', 'json'])
    probe = commands.add_parser('test-connection')
    probe.add_argument('--transport', type=Path, required=True)
    for name in ('publish','resend'):
        command=commands.add_parser(name)
        command.add_argument('--run',type=Path,required=True)
        command.add_argument('--transport',type=Path,required=True)
        if name=='publish':command.add_argument('--resume',action='store_true')
        else:command.add_argument('--publication',required=True)
    for name in ('report','compare'):
        command=commands.add_parser(name)
        command.add_argument('--run',type=Path,required=True)
        command.add_argument('--output',type=Path,required=True)
        if name=='compare':command.add_argument('--reception',type=Path,required=True)
    args = parser.parse_args()
    if args.command not in ('validate','generate'):
        return external_command(args)
    try:
        scenario = SimulationScenario.model_validate_json(args.scenario.read_text(encoding='utf-8'))
        if args.command == 'generate':
            if args.format:
                scenario = scenario.model_copy(update={'format': args.format})
            from pas600_simulator.report import generate_run
            result = generate_run(scenario, args.output)
            print(json.dumps({'schema_version': 1, 'status': 'generated', 'publications': len(result['publications'])}))
            return 0
        from pas600_simulator.report import validate_generation
        validate_generation(scenario)
        logical, complete = scenario_hashes(scenario)
    except ValidationError:
        print('Invalid scenario: check schema, topology, calendar and energy ranges.', file=sys.stderr)
        return 2
    except ValueError:
        print('Invalid generation configuration or occupied output.', file=sys.stderr)
        return 5 if args.command == 'generate' and args.output.exists() and any(args.output.iterdir()) else 2
    except (OSError, UnicodeError):
        print('Scenario cannot be read.', file=sys.stderr)
        return 5
    print('{"schema_version":1,"status":"valid","logical_hash":"' + logical + '","complete_hash":"' + complete + '"}')
    return 0


def external_command(args):
    """Dispatch transport/report commands with fixed diagnostics; never print exception bodies, configuration or secrets."""
    import asyncio
    import signal
    from pas600_simulator.transport import TransportSettings,TransferError,publish_run,test_connection
    async def execute():
        """Translate POSIX stop signals into cooperative shutdown without cancelling durable attempt cleanup."""
        stop=asyncio.Event()
        loop=asyncio.get_running_loop()
        for code in (signal.SIGINT,signal.SIGTERM):loop.add_signal_handler(code,stop.set)
        try:
            settings=TransportSettings.model_validate_json(args.transport.read_text())
            if args.command=='test-connection':return await test_connection(settings)
            return await publish_run(args.run,settings,resume=getattr(args,'resume',False),
                publication_key=getattr(args,'publication',None),stop=stop)
        finally:
            for code in (signal.SIGINT,signal.SIGTERM):loop.remove_signal_handler(code)
    try:
        if args.command=='report':
            from pas600_simulator.report import control_report
            from pas600_simulator.journal import atomic_json
            atomic_json(args.output,control_report(args.run))
            print('{"schema_version":1,"status":"reported"}');return 0
        if args.command=='compare':
            from pas600_simulator.compare import compare_run
            from pas600_simulator.journal import atomic_json
            result=compare_run(args.run,args.reception)
            atomic_json(args.output,result)
            print(json.dumps({'schema_version':1,'comparison_status':result['comparison_status']}))
            return 6 if result['differences'] else 0 if result['comparison_status']=='complete' else 5
        result=asyncio.run(execute())
        print(json.dumps(result))
        return result.get('exit_code',0)
    except TransferError as error:
        print('Transfer stopped: '+error.code,file=sys.stderr)
        return 5 if error.code in {'manifest_conflict','resume_required','publication_not_found'} else 3 if error.permanent else 4
    except ValidationError:
        print('Invalid transport configuration.',file=sys.stderr);return 2
    except (ValueError,OSError,KeyError,TypeError):
        print('Evidence or configuration cannot be read.',file=sys.stderr);return 5
