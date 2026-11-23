"""Continuously generate today's completed intervals and publish through the real SFTP CLI."""
import json
import os
from pathlib import Path
import signal
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo
from demo_profile import CHECKSUM, EVIDENCE, channels

from pas600_simulator.scenario import SimulationScenario


def scenario(now, timezone, configuration=None):
    """Build a stable daily prefix ending at the latest completed local quarter hour."""
    local = now.astimezone(ZoneInfo(timezone))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    end = local.replace(minute=local.minute//15*15, second=0, microsecond=0)
    if end <= start:
        return None
    data = SimulationScenario().model_dump(mode='json')
    data.update(timezone=timezone, start=start.isoformat(), end=end.isoformat(),
        publication_time=now.replace(microsecond=0).isoformat(), format='json', samples_per_publication=100)
    for category in data['categories']:
        meter = category['meter']
        meter.update(semantics='interval', timestamp_role='interval_end')
        meter['provenance'].update(evidence=EVIDENCE, sha256=CHECKSUM)
    if configuration:
        installed = {c['category_id']: c for c in configuration['categories']}
        for category in data['categories']:
            source = installed[category['category_id']]
            expected = next(c['source_id'] for c in channels() if c['category_id'] == category['category_id'])
            if not source['has_meter'] or source['source_id'] != expected:
                category.update(has_meter=False, meter=None, expected_range=None, rates=None)
        general = data['categories'][0]
        if general['has_meter'] and configuration.get('costs_demo',False):
            # Independent synthetic general meter, above the bounded partial loads.
            # Existing category signals and already accepted history stay byte-for-byte stable.
            upper = sum((Decimal(c['expected_range']['max']) for c in data['categories'][1:] if c['has_meter']), Decimal(0))
            general['expected_range'].update(min=str(upper + 1), max=str(upper + 5))
    return SimulationScenario.model_validate(data)


def next_boundary(now):
    """Return the next UTC quarter hour, including across local offset transitions."""
    return now.replace(minute=now.minute//15*15, second=0, microsecond=0) + timedelta(minutes=15)


def publication_start(data, last_end, configuration):
    """Skip the configuration crossing and preserve the original history when a source changes."""
    lower = max(data.start, last_end) if last_end else data.start
    if configuration.get('effective_from'):
        effective = datetime.fromisoformat(configuration['effective_from'])
        lower = max(lower, next_boundary(effective-timedelta(microseconds=1)))
    return lower


async def serve():
    """Catch up at startup, then publish newly completed intervals on calendar boundaries."""
    import asyncio
    from pas600_simulator.transport import TransportSettings, publish_run, TransferError
    from pas600_simulator.report import generate_run
    if os.environ.get('ENVIRONMENT') != 'local':
        raise RuntimeError('demo_requires_local_environment')
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for code in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(code, stop.set)
    settings = TransportSettings.model_validate_json(Path('/demo/client/transport.json').read_text())
    last_end = None
    announced = None
    while not stop.is_set():
        now = datetime.now(UTC)
        config_path = Path('/demo/configuration.json')
        if not config_path.exists():
            await asyncio.sleep(1)
            continue
        config = json.loads(config_path.read_text())
        config['costs_demo'] = Path('/demo/costs-demo-v1.json').exists()
        data = scenario(now, config['timezone'], config)
        if data and (last_end is None or data.end > last_end):
            emit_from = publication_start(data, last_end, config)
            if emit_from < data.end:
                root = Path('/demo/runs')/str(uuid4())
                generate_run(data, root, emit_from=emit_from)
                try:
                    result = await publish_run(root, settings, stop=stop)
                    print(json.dumps(dict(result, generated_from=emit_from.isoformat(), generated_until=data.end.isoformat())), flush=True)
                    if result['status'] == 'transferred':
                        last_end = data.end
                except TransferError as error:
                    print(f'Publicación demo: {error.code}', flush=True)
        delay = max(0.05, (next_boundary(datetime.now(UTC)) - datetime.now(UTC)).total_seconds())
        boundary = next_boundary(datetime.now(UTC)).astimezone(ZoneInfo(config['timezone'])).isoformat()
        if boundary != announced:
            print(json.dumps(dict(status='waiting', next_publication_at=boundary)), flush=True)
            announced = boundary
        try:
            await asyncio.wait_for(stop.wait(), min(delay, 30))
        except TimeoutError:
            pass


def main():
    """Run the local calendar publisher with cooperative signal handling."""
    import asyncio
    asyncio.run(serve())


if __name__ == '__main__':
    main()
