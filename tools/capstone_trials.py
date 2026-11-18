#!/usr/bin/env python3
"""
Capstone trials: runs criteria C1–C5 from criteria.md against a local server.

    python tools/capstone_trials.py

Each phase starts its own `serve.py` on a free port, with its own fault
setting and its own request log. Everything lands in one folder,
results/capstone_<date>_<time>/:

    report.md             every request, every check, and the tallies
    trials.json           the same, as data
    log_<phase>.jsonl     the server's request log for that phase
    server_<phase>.txt    what the server printed

Every request goes through curl, so the times are curl's `time_total`. Each
response is matched to its log line by the X-Request-Id header.

The tallies count how many trials meet each criterion's sentence. The
verdicts are written by hand.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from questions import OUT_OF_SCOPE, QUESTIONS  # noqa: E402

IN_SCOPE = [q["question"] for q in QUESTIONS]

C1_LIMIT_S = 11.0
C3_DEADLINE = "5"
C3_ATTEMPTS = 3

# C2: a run of this many characters shared by the response's `error` and the
# log's `error_detail` counts as raw SDK text in the response.
SHARED_TEXT_LIMIT = 20

C2_FAULTS = {
    "empty": (502, "empty_reply"),
    "error": (502, "model_error"),
    "ratelimit": (503, "rate_limited"),
}
BAD_BODIES = {
    "no body": None,
    "{}": "{}",
    "a list": json.dumps([IN_SCOPE[3]]),
}

MARK = "\n@@curl@@ "


# ─── Server and requests ────────────────────────────────────────────────────


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Server:
    """One `serve.py` process with its own settings and its own log."""

    def __init__(self, run_dir: Path, name: str, settings: dict):
        self.name = name
        self.settings = settings
        self.log_path = run_dir / f"log_{name}.jsonl"
        self.out_path = run_dir / f"server_{name}.txt"

    def __enter__(self):
        port = free_port()
        env = {k: v for k, v in os.environ.items() if not k.startswith("AI201_")}
        env.update(
            PORT=str(port),
            AI201_LOG_PATH=str(self.log_path),
            PYTHONUNBUFFERED="1",
            PYTHONIOENCODING="utf-8",
            **self.settings,
        )
        self.out = self.out_path.open("w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [sys.executable, "serve.py"],
            cwd=ROOT,
            env=env,
            stdout=self.out,
            stderr=subprocess.STDOUT,
        )
        self.base = f"http://127.0.0.1:{port}"
        self._wait_until_up()
        print(f"\n[{self.name}] server up on port {port}, settings {self.settings or 'none'}")
        return self

    def _wait_until_up(self, limit_s: float = 90.0) -> None:
        stop = time.monotonic() + limit_s
        while time.monotonic() < stop:
            if self.proc.poll() is not None:
                raise SystemExit(f"serve.py exited. See {self.out_path}")
            try:
                with urllib.request.urlopen(f"{self.base}/health", timeout=2) as resp:
                    health = json.load(resp)
            except OSError:
                time.sleep(0.5)
                continue
            if not health.get("index_ready"):
                raise SystemExit("No index. Run `python app.py index` first.")
            return
        raise SystemExit(f"serve.py did not come up in {limit_s:.0f}s. See {self.out_path}")

    def __exit__(self, *exc):
        self.proc.terminate()
        self.proc.wait(timeout=15)
        self.out.close()

    def log_lines(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        with self.log_path.open(encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def log_line(self, request_id: str | None) -> dict | None:
        matches = [line for line in self.log_lines() if line["request_id"] == request_id]
        return matches[0] if len(matches) == 1 else None

    def send(self, body: str | None) -> dict:
        """POST /ask through curl. `body` None sends no body at all."""
        cmd = [
            "curl", "-s", "-m", "60", "-D", "-",
            "-X", "POST", f"{self.base}/ask",
            "-H", "Content-Type: application/json",
            "-w", MARK + "%{http_code} %{time_total}",
        ]
        if body is not None:
            cmd += ["--data-binary", "@-"]
        done = subprocess.run(cmd, input=(body or "").encode("utf-8"), capture_output=True)
        out = done.stdout.decode("utf-8", "replace")

        head_and_body, _, tail = out.rpartition(MARK)
        code, seconds = tail.split()
        head, _, text = head_and_body.partition("\r\n\r\n")
        request_id = None
        for line in head.splitlines():
            name, _, value = line.partition(":")
            if name.strip().lower() == "x-request-id":
                request_id = value.strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None

        return {
            "status": int(code),
            "seconds": float(seconds),
            "request_id": request_id,
            "body": payload,
            "log": self.log_line(request_id),
        }


def question_body(question: str) -> str:
    return json.dumps({"question": question})


def short(text: str, width: int = 44) -> str:
    return text if len(text) <= width else text[: width - 1] + "…"


def shared_run(error: str | None, detail: str | None) -> int:
    """Longest run of characters `error` and `detail` have in common."""
    if not error or not detail:
        return 0
    matcher = SequenceMatcher(None, error, detail, autojunk=False)
    return matcher.find_longest_match(0, len(error), 0, len(detail)).size


def log_field(result: dict, field: str):
    return result["log"].get(field) if result["log"] else None


def yes(flag: bool) -> str:
    return "yes" if flag else "**no**"


# ─── The five criteria ──────────────────────────────────────────────────────


def run_c1(run_dir: Path) -> dict:
    rows = []
    with Server(run_dir, "hang", {"AI201_FAULT": "hang"}) as server:
        for n, question in enumerate([IN_SCOPE[0]] + IN_SCOPE[:5]):
            result = server.send(question_body(question))
            body = result["body"] or {}
            meets = (
                result["status"] == 504
                and body.get("error_kind") == "timeout"
                and result["seconds"] < C1_LIMIT_S
            )
            rows.append({
                "label": "warm-up" if n == 0 else str(n),
                "counted": n > 0,
                "question": question,
                **result,
                "meets": meets,
            })
            print(f"  C1 {rows[-1]['label']}: {result['status']} {body.get('error_kind')} {result['seconds']:.2f}s")
    return {"rows": rows}


def run_c2_faults(run_dir: Path) -> list[dict]:
    rows = []
    for fault, (status, kind) in C2_FAULTS.items():
        with Server(run_dir, fault, {"AI201_FAULT": fault}) as server:
            for question in IN_SCOPE[:3]:
                rows.append(c2_row(server.send(question_body(question)), f"{fault} fault", question, status, kind))
    return rows


def c2_row(result: dict, requests: str, question: str | None, status: int, kind: str) -> dict:
    body = result["body"] or {}
    detail = log_field(result, "error_detail")
    shared = shared_run(body.get("error"), detail)
    meets = (
        result["status"] == status
        and body.get("error_kind") == kind
        and shared < SHARED_TEXT_LIMIT
    )
    print(f"  C2 {requests}: {result['status']} {body.get('error_kind')} shared={shared}")
    return {
        "requests": requests,
        "question": question,
        "expected": f"{status} {kind}",
        **result,
        "error_detail": detail,
        "shared": shared,
        "meets": meets,
    }


def run_c3(run_dir: Path) -> dict:
    rows = []
    settings = {"AI201_FAULT": "ratelimit", "AI201_MODEL_DEADLINE": C3_DEADLINE}
    with Server(run_dir, "ratelimit_deadline5", settings) as server:
        for n, question in enumerate([IN_SCOPE[0]] + IN_SCOPE[:3]):
            result = server.send(question_body(question))
            attempts = log_field(result, "attempts")
            rows.append({
                "label": "warm-up" if n == 0 else str(n),
                "counted": n > 0,
                "question": question,
                **result,
                "attempts": attempts,
                "meets": attempts == C3_ATTEMPTS,
            })
            print(f"  C3 {rows[-1]['label']}: {result['status']} attempts={attempts}")
    return {"rows": rows}


def run_real(run_dir: Path) -> tuple[list[dict], list[dict], list[dict]]:
    """C2's bad requests, then C4 and C5, on one server with no fault."""
    c2_rows, c4_trials, c5_trials = [], [], []
    c4_requests = [
        ("answered", question_body(IN_SCOPE[0])),
        ("answered", question_body(IN_SCOPE[1])),
        ("refused", question_body(OUT_OF_SCOPE[0])),
        ("refused", question_body(OUT_OF_SCOPE[1])),
        ("bad", None),
        ("bad", "{}"),
    ]

    with Server(run_dir, "real", {}) as server:
        for name, body in BAD_BODIES.items():
            c2_rows.append(c2_row(server.send(body), f"bad request: {name}", None, 400, "bad_request"))

        for trial in range(1, 4):
            before = len(server.log_lines())
            sent = [(kind, server.send(body)) for kind, body in c4_requests]
            added = len(server.log_lines()) - before
            matched = [
                result["log"] is not None and result["log"]["status"] == result["status"]
                for _, result in sent
            ]
            c4_trials.append({
                "trial": trial,
                "lines_added": added,
                "requests": [
                    {"kind": kind, "status": r["status"], "log_status": log_field(r, "status"),
                     "outcome": log_field(r, "outcome"), "request_id": r["request_id"],
                     "seconds": r["seconds"]}
                    for kind, r in sent
                ],
                "meets": added == len(c4_requests) and all(matched),
            })
            print(f"  C4 trial {trial}: {added} lines, statuses {[r['status'] for _, r in sent]}")

        for trial in range(1, 4):
            rows = []
            for question in OUT_OF_SCOPE:
                result = server.send(question_body(question))
                refused = (result["body"] or {}).get("refused") is True
                attempts = log_field(result, "attempts")
                rows.append({
                    "question": question,
                    "status": result["status"],
                    "refused": refused,
                    "attempts": attempts,
                    "request_id": result["request_id"],
                    "meets": refused and attempts == 0,
                })
            c5_trials.append({"trial": trial, "rows": rows, "meets": all(r["meets"] for r in rows)})
            print(f"  C5 trial {trial}: {sum(r['meets'] for r in rows)} of {len(rows)}")

    return c2_rows, c4_trials, c5_trials


# ─── Report ─────────────────────────────────────────────────────────────────


def report(stamp: str, c1: dict, c2: list[dict], c3: dict, c4: list[dict], c5: list[dict]) -> str:
    c1_counted = [r for r in c1["rows"] if r["counted"]]
    c3_counted = [r for r in c3["rows"] if r["counted"]]
    c5_rows = [r for t in c5 for r in t["rows"]]

    out = [
        f"# Capstone trials — {stamp}",
        "",
        "Produced by `tools/capstone_trials.py`. Criteria are in `criteria.md` under",
        "Capstone. Logs for each phase are in this folder.",
        "",
        "## Tallies",
        "",
        "| Criterion | Target | Met |",
        "|---|---|---|",
        f"| C1 | 5 of 5 | {sum(r['meets'] for r in c1_counted)} of {len(c1_counted)} |",
        f"| C2 | 12 of 12 | {sum(r['meets'] for r in c2)} of {len(c2)} |",
        f"| C3 | 3 of 3 | {sum(r['meets'] for r in c3_counted)} of {len(c3_counted)} |",
        f"| C4 | 3 of 3 | {sum(t['meets'] for t in c4)} of {len(c4)} |",
        f"| C5 | 5 of 5 in each of 3 trials | {sum(t['meets'] for t in c5)} of {len(c5)} trials "
        f"({sum(r['meets'] for r in c5_rows)} of {len(c5_rows)} questions) |",
        "",
        "## C1 — hang fault, 504 `timeout` in under 11 s by curl",
        "",
        "| # | Question | Status | `error_kind` | curl s | Meets |",
        "|---|---|---|---|---|---|",
    ]
    for r in c1["rows"]:
        body = r["body"] or {}
        meets = yes(r["meets"]) if r["counted"] else "not counted"
        out.append(f"| {r['label']} | {short(r['question'])} | {r['status']} | "
                   f"{body.get('error_kind')} | {r['seconds']:.2f} | {meets} |")

    out += [
        "",
        "## C2 — status and `error_kind` from the table, no `error_detail` text",
        "",
        f"\"Shared\" is the longest run of characters the response's `error` has in common",
        f"with the log's `error_detail`. {SHARED_TEXT_LIMIT} or more counts as raw text in the response.",
        "A bad request never reaches the model, so its `error_detail` is null.",
        "",
        "| Requests | Question | Expected | Status | `error_kind` | Shared | Meets |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in c2:
        body = r["body"] or {}
        out.append(f"| {r['requests']} | {short(r['question'] or '—', 34)} | {r['expected']} | "
                   f"{r['status']} | {body.get('error_kind')} | {r['shared']} | {yes(r['meets'])} |")

    out += [
        "",
        f"## C3 — rate-limit fault, deadline {C3_DEADLINE} s, exactly {C3_ATTEMPTS} attempts in the log",
        "",
        "| # | Question | Status | Attempts | `model_ms` | Meets |",
        "|---|---|---|---|---|---|",
    ]
    for r in c3["rows"]:
        meets = yes(r["meets"]) if r["counted"] else "not counted"
        out.append(f"| {r['label']} | {short(r['question'])} | {r['status']} | {r['attempts']} | "
                   f"{log_field(r, 'model_ms')} | {meets} |")

    out += [
        "",
        "## C4 — 6 requests a trial, 6 new log lines, statuses match",
        "",
        "Each trial: 2 in-scope questions, 2 off-topic questions, no body, and `{}`.",
        "",
        "| Trial | Lines added | Response status → log status | Meets |",
        "|---|---|---|---|",
    ]
    for t in c4:
        pairs = ", ".join(f"{q['status']}→{q['log_status']}" for q in t["requests"])
        out.append(f"| {t['trial']} | {t['lines_added']} | {pairs} | {yes(t['meets'])} |")

    out += [
        "",
        "## C5 — off-topic questions refused, `attempts` 0 in the log",
        "",
        "| Trial | Question | Status | `refused` | Attempts | Meets |",
        "|---|---|---|---|---|---|",
    ]
    for t in c5:
        for r in t["rows"]:
            out.append(f"| {t['trial']} | {short(r['question'])} | {r['status']} | "
                       f"{r['refused']} | {r['attempts']} | {yes(r['meets'])} |")

    return "\n".join(out) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    run_dir = ROOT / "results" / f"capstone_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    print(f"Writing to {run_dir.relative_to(ROOT)}")

    c1 = run_c1(run_dir)
    c2 = run_c2_faults(run_dir)
    c3 = run_c3(run_dir)
    c2_bad, c4, c5 = run_real(run_dir)
    c2 += c2_bad

    text = report(stamp, c1, c2, c3, c4, c5)
    (run_dir / "report.md").write_text(text, encoding="utf-8")
    (run_dir / "trials.json").write_text(
        json.dumps({"c1": c1, "c2": c2, "c3": c3, "c4": c4, "c5": c5}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("\n" + text)


if __name__ == "__main__":
    main()
