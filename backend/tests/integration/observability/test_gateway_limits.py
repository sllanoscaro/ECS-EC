"""Exercise actual gateway concurrency/total timeout using a private finite fault fixture.

The fixture replaces only this007 test project's Loki listener temporarily. No public
injection endpoint or functional domain substitute exists; no business result is credited.
"""

import asyncio
import subprocess
import time
from uuid import uuid4


async def test_four_queries_and_total_thirty_second_deadline(gateway_client, gateway_root):
    """Four stalled queries finish at the total deadline; the fifth is rejected before source delivery."""
    name = "ecs007-slow-loki-" + uuid4().hex
    code = '''
"""Private backend fault, no host ports or signal persistence."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import time
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  """Wait longer than the gateway budget; no signal data or credentials are returned."""
  time.sleep(40)
  self.send_response(200);self.end_headers()
  try:self.wfile.write(b'{}')
  except BrokenPipeError:pass
 def log_message(self,*args):
  """Disable arbitrary HTTP diagnostics in the controlled fault fixture."""
  pass
ThreadingHTTPServer(('0.0.0.0',3100),Handler).serve_forever()
'''
    subprocess.run(["docker", "stop", "ecs007-validation-loki-1"], check=True, capture_output=True)
    try:
        subprocess.run(["docker", "run", "-d", "--rm", "--name", name, "--log-driver=none",
                        "--network", "ecs007-validation_technical_store", "--network-alias", "loki",
                        "ecs007-validation-app:local", "/app/.venv/bin/python", "-c", code], check=True, capture_output=True)
        await asyncio.sleep(6)  # real private DNS TTL, no public wait/injection route
        start = time.monotonic()
        requests = [gateway_client.get("/logs/loki/api/v1/query_range", params={"query": '{service_name="ecs-ec"}'}) for _ in range(5)]
        responses = await asyncio.gather(*requests)
        elapsed = time.monotonic() - start
        statuses = sorted(response.status_code for response in responses)
        assert statuses == [429, 504, 504, 504, 504]
        # Includes Basic crypt/admission overhead; each admitted subrequest has a30s timer.
        assert 29 <= elapsed < 35
    finally:
        subprocess.run(["docker", "stop", "-t", "1", name], capture_output=True)
        subprocess.run(["docker", "start", "ecs007-validation-loki-1"], check=True, capture_output=True)
