"""Nonblocking safe log admission and bounded disk worker; technical loss never raises to domain."""

from collections import deque
from copy import deepcopy
from pathlib import Path
import threading
import time
from uuid import uuid4
from loguru import logger
from ecs_ec.core.clock import SystemClock
from ecs_ec.observability.events import serialize


class LogEmitter:
    """Own1023 data slots + one replaceable control, immutable bytes and a bounded rotating spool.

    The only lock protects in-memory admission/pop/counters; no disk/network work holds
    it. A daemon worker limits shutdown even if the OS stalls a write. A process-killed
    in-flight write is not claimed delivered. Reduced limits exist only for internal tests.
    """

    def __init__(self, directory: Path, *, clock=None, autostart=True, file_bytes=16*1024*1024,
                 files=8, ttl_seconds=168*3600, writer=None):
        """Prepare memory resources without touching disk; optional worker owns all IO/errors."""
        if not 1 <= files <= 8 or not 1024 <= file_bytes <= 16*1024*1024 or ttl_seconds <= 0:
            raise ValueError("Invalid spool limits")
        self.directory, self.clock = Path(directory), clock or SystemClock()
        self.file_bytes, self.files, self.ttl = file_bytes, files, ttl_seconds
        self._data, self._control = deque(), None
        self._lock, self._wake, self._stop = threading.Lock(), threading.Event(), threading.Event()
        self._closed = False
        self._inflight = False
        self.sequence = self.dropped = self.schema_rejected = self.spool_dropped = 0
        self.boot_id = str(uuid4())
        self._index = 0
        self._writer = writer or self._write
        # Never serialize a Loguru record, extra map, exception or arbitrary message.
        logger.remove()
        self._logger = deepcopy(logger)
        self._sink = self._logger.add(self._sink_write, format="{message}", diagnose=False, backtrace=False, catch=False)
        self._thread = threading.Thread(target=self._run, name="telemetry-log-spool", daemon=True) if autostart else None
        if self._thread:
            self._thread.start()

    @property
    def depth(self):
        """Return total queued payloads, including the single replaceable control slot."""
        with self._lock:
            return len(self._data) + (self._control is not None)

    def emit(self, event, *, control=False):
        """Sanitize before admission; assign sequence even on discard; never wait for disk/network."""
        with self._lock:
            if self._closed:
                return "disabled"
            self.sequence += 1
            sequence = self.sequence
        try:
            data = serialize({**event, "sequence": sequence, "boot_id": self.boot_id})
        except Exception:
            with self._lock:
                self.schema_rejected += 1
                self.dropped += 1
            return "dropped"
        with self._lock:
            if self._closed:
                self.dropped += 1
                return "disabled"
            if control:
                self.dropped += self._control is not None
                self._control = data
            elif len(self._data) < 1023:
                self._data.append(data)
            else:
                self.dropped += 1
                return "dropped"
        self._wake.set()
        return "enqueued"

    def _sink_write(self, message):
        """Write only bytes carried by an already validated worker message; never the record."""
        self._writer(str(message).rstrip("\n").encode("utf-8"))

    def drain_one(self):
        """Pop one payload, release admission lock, then perform IO; count safe failures."""
        with self._lock:
            if self._data:
                data = self._data.popleft()
            elif self._control is not None:
                data, self._control = self._control, None
            else:
                return False
            self._inflight = True
        try:
            # Sink is worker-only; all free content was removed before the queue.
            self._logger.opt(depth=0).info(data.decode("utf-8"))
        except Exception:
            self.spool_dropped += 1
        finally:
            with self._lock:
                self._inflight = False
        return True

    def expire(self):
        """Remove only matching technical files older than policy TTL using the injected UTC clock."""
        cutoff = self.clock.now().timestamp() - self.ttl
        for path in self.directory.glob("events-*.jsonl"):
            if path.stat().st_mtime < cutoff:
                self.spool_dropped += len(path.read_bytes().splitlines())
                path.unlink()

    def _write(self, data):
        """Append within8x16MiB/TTL bounds; count rotation loss and preserve admitted byte identity."""
        import os
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.expire()
        path = self.directory / f"events-{self._index}.jsonl"
        if path.exists() and path.stat().st_size + len(data) + 1 > self.file_bytes:
            self._index = (self._index + 1) % self.files
            path = self.directory / f"events-{self._index}.jsonl"
            if path.exists():
                self.spool_dropped += len(path.read_bytes().splitlines())
                path.unlink()
        if len(data) + 1 > self.file_bytes:
            self.spool_dropped += 1
            return
        with path.open("ab") as stream:
            stream.write(data + b"\n")
        path.chmod(0o600)
        os.utime(path, (self.clock.now().timestamp(), self.clock.now().timestamp()))

    def _run(self):
        """Drain serially outside admission lock, waking for data/control or periodic expiry."""
        while not self._stop.is_set():
            self._wake.wait(0.2)
            self._wake.clear()
            while not self._stop.is_set() and self.drain_one():
                pass
            try:
                self.expire()
            except Exception:
                pass

    def shutdown(self, budget=5):
        """Stop admission, allow a bounded drain, then count/discard residual queued payloads."""
        deadline = time.monotonic() + max(0, min(5, budget))
        with self._lock:
            self._closed = True
        self._wake.set()
        while self._thread and self.depth and time.monotonic() < deadline:
            time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(max(0, deadline - time.monotonic()))
        with self._lock:
            self.dropped += len(self._data) + (self._control is not None) + self._inflight
            self._data.clear()
            self._control = None
        # Do not wait on Loguru's sink lock if an OS write is stuck. A stopped daemon
        # holds no business lock; process exit reclaims it. Each emitter has one owner.
        if not self._thread or not self._thread.is_alive():
            try:
                self._logger.remove(self._sink)
            except ValueError:
                pass
