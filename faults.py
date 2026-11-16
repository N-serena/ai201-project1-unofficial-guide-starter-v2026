"""
Fault injection for the model call.

Set AI201_FAULT and every model call goes to a fake endpoint on this machine
that misbehaves on purpose. The real SDK still makes the HTTP request and
parses the reply, so its errors and timeouts are the ones a real outage
produces. No call reaches the real service and no quota is spent.

    AI201_FAULT=hang        accepts the request and never answers
    AI201_FAULT=empty       answers 200 with an empty reply
    AI201_FAULT=ratelimit   answers 429 RESOURCE_EXHAUSTED every time
    AI201_FAULT=error       answers 500 INTERNAL every time

Every request the endpoint receives is counted, so a test can check how many
attempts the retry loop made.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KINDS = ("hang", "empty", "ratelimit", "error")

# How long a hung request is held open. Longer than any test waits.
HANG_SECONDS = 3600

_server: ThreadingHTTPServer | None = None
_hits = 0
_hits_lock = threading.Lock()


def _error_body(code: int, status: str, message: str) -> bytes:
    return json.dumps(
        {"error": {"code": code, "status": status, "message": message}}
    ).encode()


def _make_handler(kind: str):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 — name fixed by BaseHTTPRequestHandler
            global _hits
            with _hits_lock:
                _hits += 1
            length = int(self.headers.get("Content-Length") or 0)
            self.rfile.read(length)

            if kind == "hang":
                threading.Event().wait(HANG_SECONDS)
                return

            if kind == "empty":
                status = 200
                body = json.dumps(
                    {
                        "candidates": [
                            {
                                "content": {"role": "model", "parts": [{"text": ""}]},
                                "finishReason": "STOP",
                            }
                        ]
                    }
                ).encode()
            elif kind == "ratelimit":
                status = 429
                body = _error_body(
                    429, "RESOURCE_EXHAUSTED", "Injected fault: quota exceeded."
                )
            else:
                status = 500
                body = _error_body(500, "INTERNAL", "Injected fault: internal error.")

            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except OSError:
                # The client gave up first.
                pass

        def log_message(self, *args):
            pass

    return Handler


def base_url(kind: str) -> str:
    """Start the fake endpoint for this fault, once per process, and return its URL."""
    global _server
    if kind not in KINDS:
        raise ValueError(
            f"AI201_FAULT={kind!r} is not a fault. Use one of: {', '.join(KINDS)}."
        )
    if _server is None:
        _server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(kind))
        _server.daemon_threads = True
        threading.Thread(target=_server.serve_forever, daemon=True).start()
    host, port = _server.server_address[:2]
    return f"http://{host}:{port}"


def hits() -> int:
    """Requests the fake endpoint has received in this process."""
    return _hits
