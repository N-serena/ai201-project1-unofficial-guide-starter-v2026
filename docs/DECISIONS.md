# Decisions

Newest first.

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
