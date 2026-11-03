"""Internal007 transport fixture:10 synthetic operations/8 successes/2 technical failures.

Run only in an explicitly prepared test stack, on the monolith ingestion network.
No HTTP injection endpoint or business call is created. JSON stdout contains only
opaque references and technical health/cutoffs, never credentials or business inputs.
This fixture proves transport and known technical signals, not001–006 coverage.
"""

import asyncio
import json
import ssl
import time

from ecs_ec.observability import Telemetry


def main():
    """Emit a bounded reference load, observe transport for<=20s, print safe evidence and close."""
    telemetry = Telemetry.from_environment()
    if telemetry.policy is None or telemetry.policy.environment != "test":
        telemetry.shutdown()
        raise SystemExit("Reference fixture requires explicitly enabled test telemetry")
    start = telemetry.clock.now().isoformat().replace("+00:00", "Z")
    references = []
    try:
        for i in range(10):
            handle = telemetry.begin("consumption.query_detail", "consumption")
            telemetry.stage(handle, "read")
            references.append({"operation_ref": str(handle.context.operation_ref),
                               "trace_id": format(handle.span.get_span_context().trace_id, "032x")})
            telemetry.complete(handle, outcome="success" if i < 8 else "unexpected_error",
                               code="ok" if i < 8 else "database_unavailable")
        tls = ssl.create_default_context(cafile=str(telemetry.policy.ca))
        tls.load_cert_chain(str(telemetry.policy.health_cert), str(telemetry.policy.health_key))
        for _ in range(20):
            time.sleep(1)
            asyncio.run(telemetry.status.poll(telemetry.policy.health_endpoint, tls))
            if telemetry.status.snapshot()["log_collector_status"] == "available":
                break
        telemetry.health()
        time.sleep(1)
        print(json.dumps({"fixture": "transport-only-007", "start": start,
                          "cutoff": telemetry.clock.now().isoformat().replace("+00:00", "Z"),
                          "references": references, "health": telemetry.status.snapshot()}))
    finally:
        telemetry.shutdown()


if __name__ == "__main__":
    main()
