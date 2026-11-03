"""Signal-specific transport evidence and conservative heartbeat continuity, never business readiness."""

import asyncio
from datetime import datetime
import httpx
from ecs_ec.core.clock import SystemClock


class Health:
    """Bounded snapshots for independent log collection and OTLP export evidence."""

    def __init__(self, logs, traces, *, clock=None):
        """Reference only technical transports and an injected UTC/monotonic clock."""
        self.logs, self.traces, self.clock = logs, traces, clock or SystemClock()
        self.collector_status, self.last_collector_success = "unknown", None
        self.collector_dropped = None
        self._sent = None

    def observe_collector(self, *, success, dropped=None):
        """Update log evidence only; failure preserves any previous success and nullable drop count."""
        if success:
            self.collector_status = "available"
            self.last_collector_success = self.clock.now().isoformat().replace("+00:00", "Z")
        else:
            self.collector_status = "degraded"
        if type(dropped) is int and dropped >= 0:
            self.collector_dropped = dropped

    async def poll(self, endpoint, tls):
        """Read only finite Alloy transport counters over health mTLS, within a total1s deadline.

        Healthy HTTP alone is not successful collection. An absent/unrecognized counter
        yields no new evidence; inactivity preserves previous evidence/age. Raw metrics,
        labels, errors, URLs and response bodies are never stored in a log or span.
        """
        try:
            async with asyncio.timeout(1):
                async with httpx.AsyncClient(verify=tls, trust_env=False, follow_redirects=False, timeout=1) as client:
                    async with client.stream("GET", endpoint) as response:
                        if response.status_code != 200:
                            raise ValueError()
                        body = b""
                        async for chunk in response.aiter_bytes():
                            body += chunk
                            if len(body) > 65536:
                                raise ValueError()
            permitted = {"loki_write_sent_entries_total": 0, "loki_write_dropped_entries_total": 0}
            found = set()
            for line in body.decode().splitlines():
                parts = line.split()
                if len(parts) != 2:
                    continue
                name = parts[0].split("{", 1)[0]
                if name in permitted:
                    value = float(parts[1])
                    if not value.is_integer() or value < 0:
                        raise ValueError()
                    permitted[name] += int(value)
                    found.add(name)
            if "loki_write_sent_entries_total" in found:
                sent = permitted["loki_write_sent_entries_total"]
                if sent > (self._sent or 0):
                    self.observe_collector(success=True, dropped=permitted["loki_write_dropped_entries_total"])
                self._sent = sent
        except Exception:
            self.observe_collector(success=False)

    def snapshot(self):
        """Return strictly schema-defined counters/status, with null for unavailable evidence."""
        return dict(logs_dropped_total=self.logs.dropped, spans_dropped_total=self.traces.dropped,
                    schema_rejected_total=self.logs.schema_rejected, log_queue_depth=self.logs.depth,
                    span_queue_depth=self.traces.depth, spool_dropped_total=self.logs.spool_dropped,
                    collector_dropped_total=self.collector_dropped, log_collector_status=self.collector_status,
                    last_log_collector_success=self.last_collector_success, trace_export_status=self.traces.status,
                    last_trace_export_success=self.traces.last_success, trace_export_failures_total=self.traces.failures,
                    trace_exported_spans_total=self.traces.exported)


def heartbeat_continuity(last: datetime | None, now: datetime) -> str:
    """Return observed only for a nonfuture heartbeat no older than45s; never infer activity counts."""
    if last is None or not 0 <= (now - last).total_seconds() <= 45:
        return "unknown"
    return "observed"
