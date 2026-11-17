"""
The request log: one JSON object per line, one line per POST /ask.

Every request leaves a line, including bad requests and failed model calls.
Every line has every field in FIELDS, in that order. A field with nothing to
report is null.

    timestamp       when the request arrived, UTC
    request_id      also sent back in the X-Request-Id response header
    question        what came in, or null when no question could be read
    outcome         answered, refused or error
    status          the HTTP status sent back
    error_kind      bad_request, timeout, empty_reply, rate_limited,
                    model_error or internal
    error           the sentence the caller got
    answer          what went out
    sources         documents retrieved for the answer
    best_distance   closest chunk's distance, what the gate judged
    duration_ms     whole request, arrival to response
    model_ms        time inside the model call: pacing, attempts and backoff
    attempts        model attempts made. 0 when the call was never reached
    cached          true when the answer came from the local cache
    prompt_tokens   as reported by the service, summed over attempts
    output_tokens   as reported by the service, summed over attempts
    model           model name
    fault           the injected fault, or null for the real service
    error_detail    the service's raw error text, for diagnosis
    raw_body        first 200 characters of a body that held no question

The file is config.LOG_PATH.
"""

import json
import sys
import threading
from datetime import datetime, timezone

import config

FIELDS = (
    "timestamp",
    "request_id",
    "question",
    "outcome",
    "status",
    "error_kind",
    "error",
    "answer",
    "sources",
    "best_distance",
    "duration_ms",
    "model_ms",
    "attempts",
    "cached",
    "prompt_tokens",
    "output_tokens",
    "model",
    "fault",
    "error_detail",
    "raw_body",
)

_lock = threading.Lock()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write(record: dict) -> None:
    """Append one record. A failed write is reported and never fails the request."""
    unknown = set(record) - set(FIELDS)
    if unknown:
        print(f"  [log] dropped unknown fields: {sorted(unknown)}", file=sys.stderr)
    line = json.dumps({field: record.get(field) for field in FIELDS}, ensure_ascii=False)

    path = config.LOG_PATH
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _lock, path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
    except OSError as exc:
        print(f"  [log] could not write {path}: {exc}", file=sys.stderr, flush=True)


def read(path=None) -> list[dict]:
    """Every record in the log, oldest first."""
    path = path or config.LOG_PATH
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
