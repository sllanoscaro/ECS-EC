"""Shared consumer-test adapters over the installed003 simulator and actual SFTP listener.

Only synthetic scenarios and externally provisioned test credentials are used. Helpers
do not implement native formats, receipt, authentication or transport. The caller owns
the isolated PostgreSQL/listener fixtures and any injected functional clock.
"""

import asyncio
import json
import os
from pathlib import Path

import asyncssh
from sqlalchemy import select

from ecs_ec.acquisition.models import PublicationEvaluation
from ecs_ec.core.unit_of_work import UnitOfWork

SIMULATOR = "tools/pas600_simulator/.venv/bin/pas600-sim"


async def simulator_command(*arguments, environment=None):
    """Run the independent installed CLI; raise on failure without displaying credentials.

    stdout is returned as bytes. A bounded timeout kills and joins the child before
    propagating failure; captured stderr remains private because it may contain paths.
    """
    process = await asyncio.create_subprocess_exec(
        SIMULATOR, *map(str, arguments), env=environment,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 30)
    except BaseException:
        if process.returncode is None:
            process.kill()
        await process.wait()
        raise
    assert process.returncode == 0, "standalone_simulator_command_failed"
    return output


async def generated_publication(env, root, native_format="json"):
    """Generate two exact4kWh intervals of source3 with the real003 CLI, without sending them.

    Source descriptors match the trusted003 fixture. Energy expectations are explicit
    constants, independent of simulator expected files and the receiver parser.
    """
    scenario = json.loads(Path("tools/pas600_simulator/examples/seven-meters.json").read_text())
    scenario.update(
        start="2025-12-31T21:00:00-03:00", end="2025-12-31T21:30:00-03:00",
        publication_time="2025-12-31T22:00:00-03:00", timezone="America/Santiago",
        samples_per_publication=2, format=native_format,
    )
    for category in scenario["categories"]:
        if category["category_id"] != "CAT-03":
            identifier = category["category_id"]
            category.clear()
            category.update(category_id=identifier, has_meter=False)
        else:
            channel = env["binding"].channels[2]
            category["meter"].update(
                device_local_id=channel.device_local_id, reduced_id=channel.reduced_id,
                device_name=channel.device_name, csv_topic_id=channel.csv_topic_id,
                json_value_item_id=channel.json_value_item_id, initial_counter="100",
            )
            category["expected_range"].update(min="4", max="4")
    scenario["publisher"].update(
        publisher_serial=env["binding"].publisher_serial,
        publisher_remote_id=env["binding"].publisher_remote_id,
    )
    configuration = root / "scenario.json"
    configuration.write_text(json.dumps(scenario))
    run = root / "run"
    await simulator_command("generate", "--scenario", configuration, "--output", run)
    return run


async def publish_generated(env, root, run):
    """Publish one generated cycle with real003 key auth/known_hosts and its durable journal.

    The cadence directory is exclusive to this test. No wait is shortened or bypassed;
    this helper sends a single first publication, not a real-time cadence benchmark.
    """
    configuration = root / "transport.json"
    configuration.write_text(json.dumps(dict(
        destination_alias="consumer-step1", host="127.0.0.1", port=env["port"],
        directory="/", username="pas600", known_hosts_file=str(env["known"]),
        auth={"private_key_file": str(env["private"])},
    )))
    await simulator_command(
        "publish", "--run", run, "--transport", configuration,
        environment={**os.environ, "PAS600_SIM_STATE_DIRECTORY": str(root / "cadence")},
    )
    journal = [json.loads(line) for line in (run / "control/transfers.jsonl").read_text().splitlines()]
    assert len(journal) == 1 and journal[0]["session_end"] == "clean"


async def send_native(env, files):
    """Send explicit native fixtures through actual SSH/CLOSE/EOF; do not call staging directly.

    Unlike the simulator scheduler, this low-level transport allows adversarial receipt
    timing under the injected002 clock. It does not assert sender cadence compliance.
    """
    async with asyncssh.connect(
        "127.0.0.1", env["port"], username="pas600", client_keys=[str(env["private"])],
        known_hosts=str(env["known"]),
    ) as connection:
        sftp = await connection.start_sftp_client()
        try:
            for name, data in files:
                async with sftp.open(name, "xb", encoding=None) as stream:
                    await stream.write(data)
            sftp.exit()
            await sftp.wait_closed()
        except BaseException:
            connection.abort()
            raise


async def evaluations(env):
    """Read detached durable003 evaluations in a fresh transaction; never process or mutate them."""
    async with UnitOfWork(env["database"].sessions) as uow:
        rows = (await uow.session.scalars(select(PublicationEvaluation).order_by(
            PublicationEvaluation.recorded_at, PublicationEvaluation.id,
        ))).all()
        # Detach before readonly rollback expires ORM attributes; these are loaded snapshots.
        uow.session.expunge_all()
        return rows
