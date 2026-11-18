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
| 4 | Defined failure responses: empty reply and exhausted retries become a named error; `/ask` returns JSON with an error kind and a 502/503/504, never an empty answer or a bare 500 | M2 | Claude | done |
| 5 | Regression check: `test.py` plus a few real questions still answer as before | M2 | Claude runs, you read | done, with a timeout finding to decide on |
| 6 | Structured log: one JSON line per `/ask` in `logs/requests.jsonl` — timestamp, question, outcome, error kind, status code, duration, attempts, tokens. Failures logged too | M3 | Claude | done |
| 7 | `RUNNING.md` capstone section, tested from a clean clone in a fresh 3.13 venv | M3 | Claude | done |
| 8 | Cost: ten real requests, average tokens and seconds. README **Running It**, **Instrumentation** (10+ entries and a failed run) and **What It Costs** | M3 | Claude | done |
| 9 | Five capstone criteria in `criteria.md`, committed as `add capstone criteria` before any results | M4 | **You write them.** Claude only asks the three self-check questions | done: C1–C5 written, Claude checked them against the code |
| 10 | Test runner for your five criteria, three trials each; **Run Log and Verdicts** with pasted output; commit named as first results | M5 | Claude builds and runs, you check | done: every target met. Verdicts are step 11 |
| 11 | Verdicts and a stage-plus-mechanism diagnosis for every miss | M6 | You call them, Claude checks against the data | done: all five met. The slow first request is diagnosed for step 12 |
| 12 | One improvement aimed at a diagnosis, full re-run, **The Improvement** with both tables side by side | M6 | Claude builds, you decide which fix | done: startup warm-up, hang first request 13.38 s → 10.09 s, all five still met |
| 13 | Hundred-a-day arithmetic, **What's Still Broken**, the one next thing, **How I Used AI**, submission check | M7 | You write How I Used AI | in progress: hundred-a-day arithmetic done. Next is which target to tighten |

## Dependencies

- 2 comes before 3 and 4, so each hardening change can be shown failing and
  then handled.
- 6 needs 4, because the log records the error kinds 4 defines.
- 9 must be committed before 10 produces any number. The commit order is the
  evidence.
- 12 needs 11's diagnosis to aim at.
- For 10: each fault runs on its own server start, so pacing never carries
  over between C2 and C3. C2's bad requests carry no `error_detail`, so only
  its 9 fault requests test the raw-text check. C4's answered questions are
  real model calls, and can hit the 10 s timeout. That still leaves a line.

## Contracts to settle early

- **Error kinds** (fixed in step 4, used by 6 and 10), with their `/ask`
  status: `bad_request` 400, `empty_reply` 502, `model_error` 502,
  `rate_limited` 503, `timeout` 504, `internal` 500. Successful outcomes are
  `answered` and `refused`, both 200. Every error body has `error`,
  `error_kind` and `corpus`, plus `question` once one was read.
  `serve.py::ERROR_STATUS` holds the mapping.
- **Log record** (fixed in step 6): field names do not change after the first
  committed entries, so before and after runs stay comparable. The fields, in
  order, are `requestlog.FIELDS`: `timestamp`, `request_id`, `question`,
  `outcome`, `status`, `error_kind`, `error`, `answer`, `sources`,
  `best_distance`, `duration_ms`, `model_ms`, `attempts`, `cached`,
  `prompt_tokens`, `output_tokens`, `model`, `fault`, `error_detail`,
  `raw_body`. Each one is described at the top of `requestlog.py`.
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

## After step 4 (defined failure responses)

| Request | Status | Time | Hits | `error_kind` |
|---|---|---|---|---|
| fault `hang` | 504 | 12.8 s | 1 | `timeout` |
| fault `empty` | 502 | 2.6 s | 1 | `empty_reply` |
| fault `error` | 502 | 3.0 s | 1 | `model_error` |
| fault `ratelimit` | 503 | 10.0 s | 4 | `rate_limited` |
| fault `ratelimit`, deadline 5 s | 503 | 5.9 s | 3 | `rate_limited` |
| no body, `{}`, blank, number, list | 400 | 0.0–0.1 s | 0 | `bad_request` |
| none, uncached | 200 | 4.7 s | 0 | — correct answer, 658 tokens |

Before this step, a numeric question and a list body both returned an HTML
500 from Flask, checked against the step 3 `serve.py`.

## Regression check (step 5)

**`python test.py`:** 9 pass, 1 fail. The fail is the Python version: the
`.venv` is 3.14, which predates the capstone. Step 7 builds a 3.13 one. Its
model check calls the SDK directly, so it does not exercise `generate.py`.

**`python run_eval.py --label regression`:** stopped partway through run 1
with `ModelCallError: The model did not answer within 10.0s`. That was a real
call to the live service, with no fault set. No results file was written.

**Latency probe:** the five unit 2 questions, three runs, uncached, through
`generate.answer_from_chunks`, with the limits raised to 60 s per attempt and
120 s per call so nothing was cut off. Current settings: `TOP_K = 6`, hybrid
search on. Unit 2's after run used `TOP_K = 8`.

| Run | Bakery | Trams | Bus tickets | Elder Ness | Mill museum |
|---|---|---|---|---|---|
| 1 | 2.21 s | 1.09 s | 9.34 s | 7.08 s | 0.86 s |
| 2 | 0.72 s | 0.56 s | 7.30 s | **20.88 s** | 7.02 s |
| 3 | 0.97 s | 0.87 s | 0.88 s | 1.03 s | 0.85 s |

- **Answers:** 15 of 15 contain the expected string. Whether each one names a
  source was not checked.
- **Latency:** median 1.03 s. Five calls took 7–9.4 s, and one took 20.88 s.
- **Under the current limits:** 1 of 15 calls would be a 504 that used to be a
  slow success. The 20.88 s call is also past the 20 s deadline.
- **Tokens:** 9,987 for 15 calls, about 666 per call.

**Decided:** keep 10 s and 20 s. The criteria and the Milestone 6
improvement deal with the tail.

## Log probe (step 6)

Nine requests through the Flask test client, logged to a scratch file with
`AI201_LOG_PATH`. Nothing was written to `logs/`.

| Request | Outcome | Status | Kind | duration_ms | model_ms | Attempts | Tokens |
|---|---|---|---|---|---|---|---|
| fault `hang` | error | 504 | `timeout` | 12761 | 11400 | 1 | — |
| fault `empty` | error | 502 | `empty_reply` | 2666 | 1431 | 1 | — |
| fault `error` | error | 502 | `model_error` | 2428 | 1357 | 1 | — |
| fault `ratelimit` | error | 503 | `rate_limited` | 9521 | 8416 | 4 | — |
| body `not json` | error | 400 | `bad_request` | 6 | — | 0 | — |
| `{"question": 5}` | error | 400 | `bad_request` | 0 | — | 0 | — |
| out-of-scope question | refused | 200 | — | 1271 | — | 0 | — |
| in-scope, cached | answered | 200 | — | 48 | 0 | 0 | — |
| in-scope, uncached | answered | 200 | — | 3087 | 2013 | 1 | 625 / 33 |

- All nine lines have every field, in order. Each `X-Request-Id` header
  matched its line.
- `model_ms` on a process's first model call includes about 1.3 s of client
  setup. An instant fake reply logged about 1,400 ms. A long-running server
  pays this once. A one-request-per-process test pays it every time.
- The cache is on by default in the server, so a repeated question is
  served from `.cache` at no cost. Cost runs need `AI201_CACHE=0` or new
  questions.

## Clean-clone test (step 7)

Two clones of commit `2feb2eb` into the session scratch folder, each with a
new Python 3.13.15 venv and a copy of `.env`.

- **Clone 1, from Git Bash, with an empty home folder** so Chroma had to
  download the embedding model. The install took 119 s. The index took 14 s,
  including a 79.3 MB download that takes 167 MB on disk. The fresh index was
  2.5 MB. The server ran on port 5055. Health, an answer, a cached repeat, a
  refusal and a bad request all returned as expected, and each left a
  20-field log line.
- **Clone 2, the documented PowerShell lines run as written**, with the
  normal home folder, so the model was already cached. `Activate.ps1` ran
  under the current execution policy. The setup took 59 s. `python serve.py`
  served on port 5000, both `Invoke-RestMethod` lines worked, and the answer
  was logged: 3086 ms total, 2712 ms in the model, 665 / 30 tokens.
- **Not tested:** `gunicorn` on Linux or macOS, and the macOS/Linux setup
  lines.

## Session record and cost (step 8)

`.venv` rebuilt on Python 3.13.15. `python test.py`: 10 of 10. The server was
started from RUNNING.md with `AI201_CACHE=0`, then restarted with
`AI201_FAULT=hang` for one request. Fourteen lines went to
`logs/requests.jsonl`: 10 answered, 2 refused, 1 `bad_request`, 1 `timeout`.
No real call timed out this time.

| Per answered question (n = 10) | Mean | Min | Max |
|---|---|---|---|
| Tokens in | 630.0 | 587 | 665 |
| Tokens out | 35.6 | 22 | 55 |
| Tokens, in and out | 665.6 | 632 | 705 |
| `duration_ms` | 2352 | 634 | 4865 |
| `model_ms` | 2243 | 548 | 4789 |

Outside the model call, an answered request took 78 ms on average, not
counting the first request in the process.

## First capstone run (step 10)

`tools/capstone_trials.py`, run on 2026-11-18. Output is in
`results/capstone_2026-11-18_0140/` and pasted in the README under **Run Log
and Verdicts**.

| Criterion | Target | Met |
|---|---|---|
| C1 | 5 of 5 | 5 of 5, curl 10.08–10.15 s |
| C2 | 12 of 12 | 12 of 12, longest shared run 7 characters |
| C3 | 3 of 3 | 3 of 3, `model_ms` about 3,030 |
| C4 | 3 of 3 | 3 of 3 |
| C5 | 5 of 5 in each of 3 trials | 3 of 3 trials, 15 of 15 |

For step 11:

- Nothing missed, so there is no miss to diagnose. Step 12 still needs one
  improvement, so the diagnosis has to aim at something the trials show.
- The uncounted first request is where the time goes. The C1 warm-up took
  13.38 s by curl, over the 11 s a caller would see on any other request.
  The C3 warm-up spent 4,317 ms in the model call against about 3,030 for
  the rest.
- C2's 20-character rule is the runner's reading of "contains none of the
  `error_detail` text". The user should agree with it before calling C2.
- The real phase made one real model call. The cache served every other
  answered request.

## Verdicts (step 11)

The user called all five met and accepted C2's 20-character rule. A second
run, `results/capstone_2026-11-18_0145/`, matched every tally. Its C1 warm-up
took 11.81 s.

Diagnosis for step 12, in the README under **Run Log and Verdicts**: each
attempt's timeout is fixed in `generate.py::_call_with_retries` before
`_get_client()` runs. The first request's import and client build, 1.3–2.6 s,
therefore lands on top of the 10 s. The user picks the fix in step 12.

## Improvement (step 12)

The user chose to warm up at startup. `serve.py::_warm_up` runs one search
and calls `generate.warm_up()` before `app.run`, which adds 2.9 s to startup
and makes no model call. The re-run is in `results/capstone_2026-11-18_0154/`.
The first request in every phase now matches the later ones: hang 10.09 s by
curl, against 13.38 s before. C1–C5 all still met. Before and after tables
are in the README under **The Improvement**.

## Open gap, deferred by the user (step 13)

The brief's Milestones 5 and 6 ask for three full runs before the fix and
three after, in a table with Run 1, Run 2, Run 3 and MET or MISSED, plus real
log lines pasted under it. There are two before runs (`_0140`, `_0145`) and
one after (`_0154`), and the verdicts say "met". On 2026-11-18 the user chose
to finish step 13 first and close this in a later resubmission. The plan for
it: export commit `2323e75` with `git archive` into a scratch folder for the
third before run, run the current code twice more, then rewrite both run logs
in the brief's format.

## Watch-outs

- **Quota.** Failure trials use the fault switch and cost nothing. Happy-path
  trials, the cost run and the regression check do call the model. Budget
  roughly 60–100 real calls across both result sets. `SESSION_REQUEST_BUDGET`
  is 300 per process.
- **Index is git-ignored.** A clean clone must run `python app.py index` first.
- **Gunicorn does not run on Windows.** The local command is
  `python serve.py`.
- **Python version.** Resolved in step 8. The repo's `.venv` was rebuilt on
  3.13.15, and `python test.py` passes 10 of 10.
- **One log per purpose.** `logs/requests.jsonl` is the step 8 session
  record, committed and pasted in the README. Test runs from step 10 on set
  `AI201_LOG_PATH` to a file under `results/`, so each trial set has its own
  log and the session record stays as pasted.
- **Cost numbers come from step 8.** Re-measure after Milestone 6 only if
  the improvement changes the prompt or the retries.
- **README format.** Capstone section names are bold labels under one
  `## Capstone` heading, never `###`.
- **Commits.** At least eight new ones this unit, three of them in steps 2–5.
