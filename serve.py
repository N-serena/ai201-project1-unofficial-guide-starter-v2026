#!/usr/bin/env python3
"""
The Unofficial Guide — the same pipeline, over HTTP.

    python serve.py                          run it locally on port 5000
    gunicorn serve:app                       run it the way a host runs it

Nothing new happens in this file. It is a wrapper: a request comes in, it
hands the question to `app.py::ask_pipeline` — the exact function the command
line uses — and hands the answer back as JSON. Retrieval, the relevance gate
and the grounded prompt all still live where they lived. If you change how
your system answers, you change it in those files and this one follows.

Two routes:

    POST /ask       {"question": "..."} in, the answer and its sources out
    GET  /health    is the service up, and is there an index to search

Why this exists: `app.py` runs once and exits, which is fine on your laptop
and impossible to deploy. A hosted service has to stay up and wait for
requests. This is the smallest thing that does that.

Every POST /ask writes one line to the request log (`requestlog.py`), bad
requests and failures included. The response's X-Request-Id header matches
the line's `request_id`.
"""

import os
import time
import uuid

from flask import Flask, jsonify, request

import config
import requestlog

app = Flask(__name__)

# HTTP status for each error kind. The model call's kinds come from
# generate.ModelCallError.
ERROR_STATUS = {
    "bad_request": 400,
    "empty_reply": 502,
    "model_error": 502,
    "rate_limited": 503,
    "timeout": 504,
    "internal": 500,
}


def _error(kind: str, message: str, question: str | None = None):
    """One JSON shape for every failure, so a caller can branch on `error_kind`."""
    body = {"error": message, "error_kind": kind, "corpus": config.CORPUS}
    if question is not None:
        body["question"] = question
    return jsonify(body), ERROR_STATUS[kind]


@app.get("/health")
def health():
    """Is the service up, and is there an index to search?

    Two different questions, and the second one is the one that bites. A
    freshly deployed service answers this route happily while every /ask
    returns "no index" — hosts give you no disk that survives a restart, so
    the index has to be built as part of getting the service up. Checking
    here means you find that out in one request instead of five.
    """
    from store import index_exists

    ready = index_exists(config.CORPUS)
    return jsonify(
        {
            "status": "ok",
            "corpus": config.CORPUS,
            "index_ready": ready,
            "detail": (
                "ready"
                if ready
                else "no index for this corpus — run `python app.py index`"
            ),
        }
    )


@app.post("/ask")
def ask():
    """One question in, one grounded answer out.

    A refused question is a 200, not an error. The gate refusing is your
    system working — it is an answer, and the JSON says so with
    `"refused": true` so whatever calls this can tell the two apart.

    A failure returns `error` and `error_kind`, with the status from
    ERROR_STATUS.

    Every call writes one line to the request log, whatever happened.
    """
    import generate

    started = time.monotonic()
    timestamp = requestlog.now()
    request_id = uuid.uuid4().hex[:12]
    generate.reset_call_stats()

    seen = {"question": None, "error_detail": None, "raw_body": None}
    response, status = _answer(seen)
    body = response.get_json()

    if status == 200:
        outcome = "refused" if body.get("refused") else "answered"
    else:
        outcome = "error"
    requestlog.write(
        {
            "timestamp": timestamp,
            "request_id": request_id,
            "question": seen["question"],
            "outcome": outcome,
            "status": status,
            "error_kind": body.get("error_kind"),
            "error": body.get("error"),
            "answer": body.get("answer"),
            "sources": body.get("sources"),
            "best_distance": body.get("best_distance"),
            "duration_ms": round((time.monotonic() - started) * 1000),
            **generate.call_stats(),
            "model": config.MODEL,
            "fault": config.FAULT or None,
            "error_detail": seen["error_detail"],
            "raw_body": seen["raw_body"],
        }
    )
    response.headers["X-Request-Id"] = request_id
    return response, status


def _answer(seen: dict):
    """Run one /ask. Returns (response, status) and fills `seen` for the log."""
    from app import ask_pipeline
    from generate import ModelCallError, QuotaGuard

    payload = request.get_json(silent=True)
    question = payload.get("question") if isinstance(payload, dict) else None
    question = question.strip() if isinstance(question, str) else ""

    if not question:
        seen["raw_body"] = request.get_data(as_text=True)[:200]
        return _error(
            "bad_request",
            "Send JSON with a question in it, like "
            '{"question": "is the housing lottery random?"}',
        )

    seen["question"] = question
    try:
        outcome = ask_pipeline(question, corpus=config.CORPUS)
    except ModelCallError as exc:
        seen["error_detail"] = exc.detail
        return _error(exc.kind, str(exc), question)
    except QuotaGuard:
        return _error(
            "rate_limited",
            "This server has used its request budget for the session.",
            question,
        )
    except Exception as exc:  # noqa: BLE001 — a reader gets this, not a traceback
        return _error("internal", f"{type(exc).__name__}: {exc}", question)

    return (
        jsonify(
            {
                "question": question,
                "answer": outcome["answer"],
                "refused": outcome["refused"],
                "sources": outcome["sources"],
                "best_distance": round(outcome["best_distance"], 4),
                "threshold": outcome["threshold"],
                "corpus": config.CORPUS,
            }
        ),
        200,
    )


def main():
    # Hosts tell you which port to listen on through PORT, and they expect you
    # on 0.0.0.0. Binding 127.0.0.1 instead works perfectly on your laptop and
    # then answers nothing at all once deployed, because the host's router
    # can't reach a socket that only accepts connections from inside the
    # container. It is the single most common way a first deploy "succeeds"
    # and is unreachable.
    port = int(os.getenv("PORT", "5000"))

    # Debug mode reloads on save, which is handy, and prints a console that
    # runs arbitrary code, which is not something to leave switched on where
    # strangers can reach it. Off unless you ask for it.
    debug = os.getenv("AI201_DEBUG", "0") == "1"

    print(f"Serving The Unofficial Guide on http://localhost:{port}")
    print(f"Corpus: {config.CORPUS}    (Ctrl-C to stop)\n")
    print("Try it from another terminal:\n")
    print(f"  curl http://localhost:{port}/health")
    print(
        f"  curl -X POST http://localhost:{port}/ask \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"question\": \"is the housing lottery random?\"}}'\n"
    )

    app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
