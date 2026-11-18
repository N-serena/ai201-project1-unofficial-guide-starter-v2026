# Capstone trials — 2026-11-18_0140

Produced by `tools/capstone_trials.py`. Criteria are in `criteria.md` under
Capstone. Logs for each phase are in this folder.

## Tallies

| Criterion | Target | Met |
|---|---|---|
| C1 | 5 of 5 | 5 of 5 |
| C2 | 12 of 12 | 12 of 12 |
| C3 | 3 of 3 | 3 of 3 |
| C4 | 3 of 3 | 3 of 3 |
| C5 | 5 of 5 in each of 3 trials | 3 of 3 trials (15 of 15 questions) |

## C1 — hang fault, 504 `timeout` in under 11 s by curl

| # | Question | Status | `error_kind` | curl s | Meets |
|---|---|---|---|---|---|
| warm-up | What time does the bakery in Kestrelford se… | 504 | timeout | 13.38 | not counted |
| 1 | What time does the bakery in Kestrelford se… | 504 | timeout | 10.15 | yes |
| 2 | How often do Marchwood's trams run on weekd… | 504 | timeout | 10.10 | yes |
| 3 | Why do visitors get caught out by bus ticke… | 504 | timeout | 10.11 | yes |
| 4 | When does the road to Elder Ness flood? | 504 | timeout | 10.09 | yes |
| 5 | How long should I allow for the mill museum… | 504 | timeout | 10.08 | yes |

## C2 — status and `error_kind` from the table, no `error_detail` text

"Shared" is the longest run of characters the response's `error` has in common
with the log's `error_detail`. 20 or more counts as raw text in the response.
A bad request never reaches the model, so its `error_detail` is null.

| Requests | Question | Expected | Status | `error_kind` | Shared | Meets |
|---|---|---|---|---|---|---|
| empty fault | What time does the bakery in Kest… | 502 empty_reply | 502 | empty_reply | 2 | yes |
| empty fault | How often do Marchwood's trams ru… | 502 empty_reply | 502 | empty_reply | 2 | yes |
| empty fault | Why do visitors get caught out by… | 502 empty_reply | 502 | empty_reply | 2 | yes |
| error fault | What time does the bakery in Kest… | 502 model_error | 502 | model_error | 7 | yes |
| error fault | How often do Marchwood's trams ru… | 502 model_error | 502 | model_error | 7 | yes |
| error fault | Why do visitors get caught out by… | 502 model_error | 502 | model_error | 7 | yes |
| ratelimit fault | What time does the bakery in Kest… | 503 rate_limited | 503 | rate_limited | 3 | yes |
| ratelimit fault | How often do Marchwood's trams ru… | 503 rate_limited | 503 | rate_limited | 3 | yes |
| ratelimit fault | Why do visitors get caught out by… | 503 rate_limited | 503 | rate_limited | 3 | yes |
| bad request: no body | — | 400 bad_request | 400 | bad_request | 0 | yes |
| bad request: {} | — | 400 bad_request | 400 | bad_request | 0 | yes |
| bad request: a list | — | 400 bad_request | 400 | bad_request | 0 | yes |

## C3 — rate-limit fault, deadline 5 s, exactly 3 attempts in the log

| # | Question | Status | Attempts | `model_ms` | Meets |
|---|---|---|---|---|---|
| warm-up | What time does the bakery in Kestrelford se… | 503 | 3 | 4317 | not counted |
| 1 | What time does the bakery in Kestrelford se… | 503 | 3 | 3037 | yes |
| 2 | How often do Marchwood's trams run on weekd… | 503 | 3 | 3036 | yes |
| 3 | Why do visitors get caught out by bus ticke… | 503 | 3 | 3030 | yes |

## C4 — 6 requests a trial, 6 new log lines, statuses match

Each trial: 2 in-scope questions, 2 off-topic questions, no body, and `{}`.

| Trial | Lines added | Response status → log status | Meets |
|---|---|---|---|
| 1 | 6 | 200→200, 200→200, 200→200, 200→200, 400→400, 400→400 | yes |
| 2 | 6 | 200→200, 200→200, 200→200, 200→200, 400→400, 400→400 | yes |
| 3 | 6 | 200→200, 200→200, 200→200, 200→200, 400→400, 400→400 | yes |

## C5 — off-topic questions refused, `attempts` 0 in the log

| Trial | Question | Status | `refused` | Attempts | Meets |
|---|---|---|---|---|---|
| 1 | What is the capital of Mongolia? | 200 | True | 0 | yes |
| 1 | How do I change the oil in a diesel engine? | 200 | True | 0 | yes |
| 1 | Who won the 1994 World Cup? | 200 | True | 0 | yes |
| 1 | What is the recommended dosage of ibuprofen… | 200 | True | 0 | yes |
| 1 | How do I write a for loop in Rust? | 200 | True | 0 | yes |
| 2 | What is the capital of Mongolia? | 200 | True | 0 | yes |
| 2 | How do I change the oil in a diesel engine? | 200 | True | 0 | yes |
| 2 | Who won the 1994 World Cup? | 200 | True | 0 | yes |
| 2 | What is the recommended dosage of ibuprofen… | 200 | True | 0 | yes |
| 2 | How do I write a for loop in Rust? | 200 | True | 0 | yes |
| 3 | What is the capital of Mongolia? | 200 | True | 0 | yes |
| 3 | How do I change the oil in a diesel engine? | 200 | True | 0 | yes |
| 3 | Who won the 1994 World Cup? | 200 | True | 0 | yes |
| 3 | What is the recommended dosage of ibuprofen… | 200 | True | 0 | yes |
| 3 | How do I write a for loop in Rust? | 200 | True | 0 | yes |
