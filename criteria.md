# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:** Four of my five questions have their answer sitting in a
single sentence under a `##` heading, which is the shape this corpus is written
in, so I expect those to be found. The fifth — how long to allow for
Brightwater's mill museum — I expect to be the hard one, and 4 of 5 is me
saying so in advance. "Mill" names a whole other document in this corpus:
`guide_givens_mill.md` is a village built around a working watermill that runs
mill tours, so a question containing "mill" has an entire document of close
lexical competition that is about somewhere else entirely. Setting this to 5 of
5 would mean claiming that ambiguity won't bite.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:** All five, because naming a source is the one thing here
that doesn't depend on retrieval being any good. `store.py` carries the source
filename as metadata on every chunk, and `generate.py` is handed those
filenames with the prompt, so an answer without a source means either the
prompt template stopped asking for one or the gate let through a question with
nothing retrieved at all. Both are bugs rather than bad luck, so a target that
tolerates one failure would be tolerating a bug.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:** Written before measuring — the distances go in at
Milestone 4. My prediction is a wide gap for four of the five: diesel engines,
the 1994 World Cup, ibuprofen and Rust share no vocabulary at all with a corpus
about nine towns, their buses and their opening hours. The one I expect to sit
closest is "What is the capital of Mongolia?", because these documents are
saturated with place-and-population language — Marchwood is described as the
regional hub of 180,000, Kestrelford as a town of 12,000 — and a question about
a capital city is the same shape as a question this corpus does answer. So 4 of
5, with the geography-shaped one named in advance as the one that might slip
through.

**Measured at Milestone 4** (the target above is unchanged — this fills in the
numbers the section asked for). The gap is clean and much wider than I
expected. In-corpus best distances ran 0.2437 to 0.6295; out-of-corpus ran
0.8026 to 0.9753, so nothing overlaps and the gap is 0.17 wide. Cutoff set to
0.72, in the middle of it.

The prediction was half right. Mongolia is the closest of the five at 0.8026,
exactly as reasoned, and it is still 0.08 clear of the cutoff. Naming it as the
one that might slip through overstated the risk.

---

## 4. Chunks start where the documents do

All five chunks I sample in Milestone 3 begin at a document title or a `##`
section heading rather than mid-sentence, and no chunk in the whole index is
shorter than 150 characters.

**Why this target:** Every document in `city_guides` is a title followed by
labelled sections — *Getting there*, *Getting around*, *Eat and drink*, *What
to see*, *Where to stay*, *When to go*, *Practical notes* — and each section is
one self-contained topic of roughly 200 to 450 characters. The heading is where
the meaning changes, so it is the only boundary worth cutting on.

The shipped fixed-size chunker does not cut there, and I can already show it
rather than predict it. Indexing at the default 800/120 produced 51 chunks with
a shortest length of 24 characters, which cannot be more than a stray heading
with nothing under it. And retrieving "how do I get to Kestrelford?" returned a
chunk from `guide_accessibility.md` beginning `on.  **Brightwater** is level
along the river` — a chunk that opens on the tail of a word.

150 rather than 200 because `guide_seasons.md` has the shortest sections in the
corpus and I would rather the floor catch genuine fragments than trip over a
short real section.



---

## 5. The source named is the right source

For at least 4 of my 5 test questions, the document the answer names is one
that actually contains the fact stated — not merely some document.

**Why this target:** Criterion 2 only asks whether a source appears, and in
this corpus that is a weak thing to ask. Nine of the fourteen documents end
with the same four sentences, byte for byte:

```
Cash is still useful at the market and in smaller places, though cards are
accepted almost everywhere now. Mobile coverage is good in the centre and
patchy on the outskirts. The nearest full hospital is in Brightwater; there is
a minor injuries unit locally with limited hours.
```

Every town guide carries it, including `guide_marchwood.md` — so Marchwood's
own guide says the nearest full hospital is in Brightwater, while
`guide_accessibility.md` says the nearest full hospital is in Marchwood. The
corpus contradicts itself, and for any question that lands on that paragraph
there are nine identical chunks to cite and no way to tell them apart. A system
can satisfy criterion 2 perfectly while naming a document that has nothing to
do with the answer.

4 of 5 rather than 5 of 5 for the same reason as criterion 1: the mill museum
question is the one where I expect `guide_givens_mill.md` to be retrieved and
cited for a fact that lives in `guide_brightwater.md`.



---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->

---

## Capstone

Five criteria for the hardened model call, written before any capstone results.
Each trial runs locally with `python serve.py`. A fault is set with
`AI201_FAULT` when the server starts.

**C1.**

With the hang fault set, every in-scope request after the first returns a 504
`timeout` in under 11 seconds by curl's timer, 5 of 5.

**Why this target:** the extra second over the 10-second timeout covers
retrieval overhead. A longer wait looks like the app froze.

**C2.**

For each of the empty, error and rate-limit faults, 3 in-scope requests, and
for bad requests (no body, `{}`, a list), 3 requests each get the status and
`error_kind` from the table, and the response's `error` contains none of the
log's `error_detail` text, 12 of 12.

| Requests | Status | `error_kind` |
|---|---|---|
| empty fault | 502 | `empty_reply` |
| error fault | 502 | `model_error` |
| rate-limit fault | 503 | `rate_limited` |
| bad request | 400 | `bad_request` |

**Why this target:** the mapping is fixed, so one miss means a bug. A caller
may be misled by a wrong observation.

**C3.**

With the rate-limit fault and `AI201_MODEL_DEADLINE=5`, every in-scope request
after the first logs exactly 3 attempts, 3 of 3.

**Why this target:** fewer attempts might miss, and more attempts mean a longer
wait and possibly waste.

**C4.**

On the real server, each trial of 6 requests (2 answered, 2 refused, 2 bad
requests) adds exactly 6 new lines to the log, and each line's `status` matches
the response's status code, 3 of 3.

**Why this target:** for better debugging. A missing line, or a line with the
wrong status, increases debugging overhead.

**C5.**

On the real server, each of the 5 off-topic questions in `questions.py` gets a
response with `"refused": true` and a log line with `attempts` 0, 5 of 5 in
each of 3 trials.

**Why this target:** one getting through increases misread data. A refused
question reaching the model signals an issue, like a request failure.
