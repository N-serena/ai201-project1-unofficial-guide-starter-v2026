# Decisions

Newest first.

---

## 2026-11-18 — C2's raw-text check counts 20 shared characters

**Decision:** the trial runner reads "the response's `error` contains none of
the log's `error_detail` text" as: the longest run of characters the two share
is under 20.

**Why:** the response and the raw error can share ordinary words like "model"
without leaking anything. A run of 20 characters is longer than any common
word, and shorter than the smallest piece of an SDK message worth hiding, such
as `500 INTERNAL. {'error'`. The longest run in both trial runs was 7. The user
accepted the rule before calling C2 met.

---

## 2026-11-16 — Cost is reported in tokens and seconds, measured from the log

**Decision:** the cost per run is the mean of the token counts the service
reported, and of the logged times, over ten uncached answered questions from
one real session. No dollar figure goes in until Milestone 7, and only from
a per-token price the user reads off the provider's pricing page.

**Why:** the brief asks for a measurement. Tokens and seconds are what the
system recorded. The session ran on the free tier, so it spent $0, and a
dollar figure would multiply a measurement by a price nobody in this session
has checked.

**Also:** `logs/requests.jsonl` holds only that session and is committed as
the run record. Later test runs write their own logs with `AI201_LOG_PATH`.

---

## 2026-11-16 — The request log

**Decision:** `serve.py` writes one JSON line per `POST /ask` to
`logs/requests.jsonl` through `requestlog.py`. Every line carries the same
twenty fields in the same order, null when there's nothing to report.
`generate.py` keeps per-call stats (attempts, model time, tokens, cache hit)
in a thread-local record that the route reads after the pipeline returns or
raises. `AI201_LOG_PATH` sends a test run to its own file. `logs/` is not
git-ignored, so the run record can be committed.

**Why:**

- The fixed shape means before and after runs can be compared line for line.
- A bad request or a failed call writes its line on the same path as a
  success, so a failure can't show up only as a missing line.
- `model_ms` next to `duration_ms` separates time spent on the model from
  retrieval, which is what the step 5 latency finding needs.
- The stats are thread-local because Flask's development server handles each
  request on its own thread.
- A failed log write is printed and never fails the request.

**Not logged:** the command line and `run_eval.py`. The run path is the
server, and the eval writes its own results file.

---

## 2026-11-16 — Error kinds, status codes and what the caller sees

**Decision:** `generate.py` raises `ModelCallError` with a `kind`, a sentence
for the caller, and the raw service error in `detail`. `serve.py` maps each
kind to a status: 502 for `empty_reply` and `model_error`, 503 for
`rate_limited`, 504 for `timeout`, 400 for `bad_request`, 500 for `internal`.
The response carries the sentence. `detail` is kept for the log in step 6.

**Why:**

- 502 means the upstream service sent something unusable, which is what an
  empty reply and a service error are. 503 says try later. 504 says the
  upstream took too long. A caller can act on each one differently.
- Raw exception text leaked the SDK's internals into every unit 2 error
  response. The caller now gets a sentence, and the raw text goes to the log.
- `ModelCallError` subclasses `RuntimeError`, so the CLI's existing handler
  prints it unchanged.
- `internal` covers anything outside the model call, like a missing index.
  It's a sixth kind beyond the five planned, so no failure leaves without one.
- Checking that `question` is a string fixes an HTML 500 on a numeric question
  or a list body. It's outside the model call, but it's the one bad-request
  path that crashed, and the fix is two lines.

**Trade-off:** `run_eval.py` catches nothing. An empty reply used to be scored
as an empty answer. It now stops the eval run with `ModelCallError`, the way a
rate-limit failure already did.

---

## 2026-11-16 — 10 s per attempt, 20 s per call, no retry after a timeout

**Decision:** each model attempt gets `MODEL_TIMEOUT` (10 s) or whatever is
left of `MODEL_DEADLINE` (20 s), whichever is smaller. The deadline covers
pacing, every attempt and every backoff. A timed-out attempt ends the call. A
backoff or pacing wait that would pass the deadline ends the call without
sleeping. The loop no longer sleeps after its last attempt. Both values can be
set from the environment (`AI201_MODEL_TIMEOUT`, `AI201_MODEL_DEADLINE`).

**Why:**

- A real answer took 3.5 s end to end, with the model call inside that. 10 s
  leaves roughly three times that for a slow reply.
- 20 s is about as long as a person waits on one question before giving up.
- A service that hung for 10 s is unlikely to answer on the next try, and a
  retry would spend the rest of the deadline finding that out.
- The timeout is set per request through the SDK's `http_options`, so it
  interrupts the real socket wait. `httpx` is imported directly to catch its
  timeout. It arrives with `google-genai`, so `requirements.txt` is unchanged.

**Trade-off:** pacing now counts against the deadline. A batch of more than 30
calls in a minute gets deadline errors where it used to wait. Unit 2's eval
runs stay well under that.

**Revisited in step 5:** the first reason rested on one sample. Fifteen real
calls had a median of 1.03 s, five calls between 7 and 9.4 s, and one at
20.88 s, so 10 s cuts off about 1 in 15. The limits are unchanged until the
user decides. The data is in `docs/PLAN.md` under Regression check.

---

## 2026-11-16 — Faults are injected at the HTTP layer

**Decision:** `AI201_FAULT` points the Gemini client at a fake endpoint in
`faults.py`, served on `127.0.0.1` inside the same process. It hangs, returns an
empty reply, returns 429, or returns 500. The cache is bypassed while a fault
is set, and the client uses a dummy key.

**Why:** the real SDK still sends the request, waits on the socket, and builds
its own exceptions. The retry loop matches on the text of those exceptions, so
a raised Python exception would test a message the SDK never produces. A hang
on a real socket is also the only kind of hang an HTTP timeout can interrupt.
No call reaches the real service, so failure trials cost no quota.

---

## 2026-11-16 — Capstone criteria go in the existing `criteria.md`

**Decision:** add a `## Capstone` heading at the end of `criteria.md` and put
the five new numbered criteria under it. The unit 1 criteria stay where they
are.

**Why:** the brief names `criteria.md`, and the repo already has one. Appending
keeps the file name the grader expects and leaves the earlier history intact.
A commit that touches only that section shows the criteria existed before the
results.

**Open:** confirm with the TF that a section in the existing file is acceptable.
If not, the fallback is a separate file with a pointer from `criteria.md`.

---

## 2026-11-16 — Run locally with `python serve.py` on Python 3.13

**Decision:** Path B. The start command is `python serve.py`, in a venv built
from Python 3.13.

**Why:** gunicorn does not run on Windows, so the host-style command cannot be
the local one. The pins support 3.11–3.13. The current `.venv` is 3.14, which
happens to work but is outside what `requirements.txt` promises, and the
clean-clone test has to match the promise.

---

## 2026-11-16 — Work on `main`

**Decision:** capstone commits go straight onto `main`.

**Why:** the submission is the repo URL, and graders read the default branch.

---

## 2026-11-16 — Capstone: project 1, shape B

**Decision:** extend The Unofficial Guide by hardening the model call, so every
`/ask` returns a defined JSON response within a fixed time.

**Why:**

- One model call per question keeps happy-path trials cheap on the free tier.
- Each failure can be triggered on demand without spending quota.
- The weak points are real. The model call has no timeout, an empty reply goes
  out as an empty answer, and exhausted retries surface as a bare 500.
- The unit 2 targets were admittedly set low, so new criteria have room to miss.

**Considered:** project 4 with shape A. Its audit log already exists and it
costs no API money, but less of the work would be new. Project 3 has no service
and no saved model. Project 2 makes several model calls per run, which strains
the quota across many trials.
