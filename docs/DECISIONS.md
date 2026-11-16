# Decisions

Newest first.

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
