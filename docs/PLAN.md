# Capstone plan — The Unofficial Guide, shape B

**Claim when finished:** every `POST /ask` comes back with a defined JSON
response within a fixed time, whatever the model does — answers, hangs,
returns nothing, or keeps rate-limiting.

- **System:** project 1, The Unofficial Guide (RAG over `city_guides`).
- **Shape:** B — harden against failure. The extension is the failure layer
  around the model call.
- **Run path:** Path B — local, `python serve.py`, Python 3.13, with a
  committed structured log.
- **Branch:** `main`.

One step per session turn. Each step ends with a commit command.

## Steps

Status: `todo` · `doing` · `done`

| # | Step | Milestone | Who writes it | Status |
|---|---|---|---|---|
| 0 | `docs/PLAN.md` and `docs/DECISIONS.md` | — | Claude | done |
| 1 | README `## Capstone` with **What This Extends** and **The Shape**, including out of scope | M1 | You decide, Claude drafts | done |
| 2 | Fault switch: an env var that makes the model call time out, return empty, error, or rate-limit on demand, with no API call | M2 | Claude | done |
| 3 | Timeout on each model attempt, plus one overall deadline across retries | M2 | Claude | done |
| 4 | Defined failure responses: empty reply and exhausted retries become a named error; `/ask` returns JSON with an error kind and a 503/504, never an empty answer or a bare 500 | M2 | Claude | todo |
| 5 | Regression check: `test.py` plus a few real questions still answer as before | M2 | Claude runs, you read | todo |
| 6 | Structured log: one JSON line per `/ask` in `logs/requests.jsonl` — timestamp, question, outcome, error kind, status code, duration, attempts, tokens. Failures logged too | M3 | Claude | todo |
| 7 | `RUNNING.md` capstone section, tested from a clean clone in a fresh 3.13 venv | M3 | Claude | todo |
| 8 | Cost: ten real requests, average tokens and seconds. README **Running It**, **Instrumentation** (10+ entries and a failed run) and **What It Costs** | M3 | Claude | todo |
| 9 | Five capstone criteria in `criteria.md`, committed as `add capstone criteria` before any results | M4 | **You write them.** Claude only asks the three self-check questions | todo |
| 10 | Test runner for your five criteria, three trials each; **Run Log and Verdicts** with pasted output; commit named as first results | M5 | Claude builds and runs, you check | todo |
| 11 | Verdicts and a stage-plus-mechanism diagnosis for every miss | M6 | You call them, Claude checks against the data | todo |
| 12 | One improvement aimed at a diagnosis, full re-run, **The Improvement** with both tables side by side | M6 | Claude builds, you decide which fix | todo |
| 13 | Hundred-a-day arithmetic, **What's Still Broken**, the one next thing, **How I Used AI**, submission check | M7 | You write How I Used AI | todo |

## Dependencies

- 2 comes before 3 and 4, so each hardening change can be shown failing and
  then handled.
- 6 needs 4, because the log records the error kinds 4 defines.
- 9 must be committed before 10 produces any number. The commit order is the
  evidence.
- 12 needs 11's diagnosis to aim at.

## Contracts to settle early

- **Error kinds** (fixed in step 4, used by 6 and 10): `timeout`, `empty_reply`,
  `rate_limited`, `model_error`, `bad_request`. Successful outcomes are
  `answered` and `refused`.
- **Log record** (fixed in step 6): field names do not change after the first
  committed entries, so before and after runs stay comparable.
- **Fault names** (fixed in step 2): `AI201_FAULT` is `hang`, `empty`,
  `ratelimit` or `error`. Unset means the real service.

## Baseline behaviour under each fault (step 2, before hardening)

One question through `/ask` via the Flask test client, before any hardening.
These are development checks, not criterion results.

| Fault | Status | Time | Endpoint hits | What the caller got |
|---|---|---|---|---|
| `empty` | 200 | 2.4 s | 1 | `"answer": ""`, `refused: false` |
| `error` | 500 | 2.3 s | 1 | raw `ServerError: 500 INTERNAL ...` text |
| `ratelimit` | 500 | 17.2 s | 4 | raw `RuntimeError: Still pushed back after 4 attempts ...` |
| `hang` | — | never | — | no response. Killed at 30 s |

Notes for steps 3 and 4:

- The SDK makes no retries of its own. Endpoint hits equal the attempts made
  by the retry loop in `generate.py`.
- The retry loop sleeps after the last attempt too. 8 of the 17.2 s under
  `ratelimit` is a wait that leads to no further attempt.

## After step 3 (timeout and deadline)

Same probe. Defaults: 10 s per attempt, 20 s for the whole call.

| Fault | Status | Time | Endpoint hits | What the caller got |
|---|---|---|---|---|
| `hang` | 500 | 12.7 s | 1 | `RuntimeError: The model did not answer within 10.0s` |
| `ratelimit` | 500 | 9.5 s | 4 | `RuntimeError: Still pushed back after 4 attempts ...` |
| `ratelimit`, deadline 5 s | 500 | 5.7 s | 3 | `RuntimeError: Ran out of the 5s deadline ...` |
| `empty` | 200 | 2.7 s | 1 | unchanged: `"answer": ""`. Step 4 |
| `error` | 500 | 2.5 s | 1 | unchanged: raw `ServerError` text. Step 4 |
| none, uncached | 200 | 3.5 s | 0 | correct answer, 1 real call, 658 tokens |

The probe's time includes about 2.5 s of retrieval and model loading before
the model call starts, so `hang` lands at the 10 s timeout plus that.

## Watch-outs

- **Quota.** Failure trials use the fault switch and cost nothing. Happy-path
  trials, the cost run and the regression check do call the model. Budget
  roughly 60–100 real calls across both result sets. `SESSION_REQUEST_BUDGET`
  is 300 per process.
- **Index is git-ignored.** A clean clone must run `python app.py index` first.
- **Gunicorn does not run on Windows.** The local command is
  `python serve.py`.
- **Python version.** The current `.venv` is 3.14, but the pins say 3.11–3.13.
  The clean-clone test uses 3.13.
- **README format.** Capstone section names are bold labels under one
  `## Capstone` heading, never `###`.
- **Commits.** At least eight new ones this unit, three of them in steps 2–5.
