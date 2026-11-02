"""Standalone CLI; validate without filesystem writes, network or backend imports."""
import argparse
import json
import sys
from pathlib import Path
from pydantic import ValidationError
from pas600_simulator.scenario import SimulationScenario
from pas600_simulator.identity import scenario_hashes


def main() -> int:
    """Validate or generate a strict scenario; return 0, configuration 2 or evidence 5."""
    parser = argparse.ArgumentParser(prog='pas600-sim')
    commands = parser.add_subparsers(dest='command', required=True)
    validate = commands.add_parser('validate')
    validate.add_argument('--scenario', type=Path, required=True)
    generate = commands.add_parser('generate')
    generate.add_argument('--scenario', type=Path, required=True)
    generate.add_argument('--output', type=Path, required=True)
    generate.add_argument('--format', choices=['csv', 'json'])
    args = parser.parse_args()
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
