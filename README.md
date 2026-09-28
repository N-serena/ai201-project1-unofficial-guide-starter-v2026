# The Unofficial Guide

Serena, corpus: city_guides

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Unit 1

## What This Does

This is a question-answering system over `city_guides`, a set of fourteen
travel guides to an invented region — nine town guides plus five that cut
across all of them on eating, walking, regional transport, seasons and
accessibility. You ask it a plain question about the region and it retrieves
the passages most likely to hold the answer, then has a model write a short
answer from those passages and name the document it used.

It answers specific, factual questions about the places in those guides: when
the bakery in Kestrelford sells out, how often Marchwood's trams run, when the
road to Elder Ness floods. It is deliberately narrow. A relevance gate measures
how close the retrieved passages are to the question and refuses anything the
documents do not cover, so asking it about diesel engines or the 1994 World Cup
gets you a refusal instead of an invented answer.

## Chunking Strategy

**Chunk size:** 600 characters, as a ceiling rather than a target. One chunk is
one `##` section.
**Overlap:** 0

Chunks are cut at `##` section headings, not at a character count. Every
document in `city_guides` is a `# Title` followed by labelled sections —
*Getting there*, *Getting around*, *Eat and drink*, *What to see*, *Where to
stay*, *When to go*, *Practical notes* — and I measured the 14 documents before
picking anything: **98 sections, averaging 291 characters, longest 708**. Each
section is one self-contained topic. The heading is where the subject changes,
so it is the boundary worth cutting on.

The 600 ceiling only does something in two places, where a section holds
several separate answers instead of one. `guide_accessibility.md` → *Straightforward*
was 708 characters covering Thornby Wells, Marchwood and Brightwater in three
bolded paragraphs; a question about one of those three was competing with the
other two inside the same chunk. Over the ceiling, a section is broken at a
blank line, which puts those towns in separate chunks. That took the corpus
from 94 chunks to 96.

**Every chunk carries its document title and section heading as a prefix.**
This is the part that matters most, and it fixes two things I found in the
documents:

1. A section body says "Buses run four times a day" and never names the town.
   On its own that chunk cannot answer anything. With `# Halden Bay` on the
   front, it can.
2. Nine of the fourteen documents end with a byte-identical *Practical notes*
   paragraph. Without a title prefix those are nine indistinguishable chunks;
   with one they are nine distinct chunks that name their own town.

Overlap is 0 because the title-and-heading prefix supplies the context that
overlap was there to provide. Neighbouring sections are about different
subjects, so bleeding 120 characters of *Getting around* into *Eat and drink*
adds noise to both.

**What this changed, measured.** The shipped `fallback_split` at 800/120 gave
51 chunks, averaging 650 characters, **shortest 24** — a heading with nothing
under it. Retrieving *"how do I get to Kestrelford?"* returned a chunk that
began `on.  **Brightwater** is level along the river`, opening on the tail of a
word. `split_documents` gives **96 chunks, averaging 315, shortest 174, longest
610**, and all 96 begin at a title or a `##` heading.

One honest wrinkle: the longest chunk is 610, above the 600 ceiling. The
ceiling is applied to the section body, and the title and heading are added
afterwards, so a finished chunk runs a few characters over. I left it there,
since nothing depends on the exact boundary.

**The title prefix has a cost, and I found it by measuring.** Re-running the
same question after re-indexing:

| | fallback_split | split_documents |
|---|---|---|
| Best distance for *"how do I get to Kestrelford?"* | 0.4449 | 0.3674 |
| Top-5 results from `guide_kestrelford.md` | 1 of 5 | 4 of 5 |
| Rank of the *Getting there* section | — | **7th** |

Picking the right document got clearly better. Picking the right *section
within* that document got worse. Every Kestrelford chunk now opens with
`# Kestrelford`, so they all look alike to the embedding, and for a question
about getting there the model was handed *Where to stay*, *Getting around* and
*Eat and drink* ahead of the section that answers it. At `TOP_K = 5` the
correct chunk is not retrieved at all.

I am leaving this in place for unit 1 and carrying it into unit 2 as a known
weakness. It is a live risk to criterion 1, and the shape of the fix is already
visible — the title is doing too much work in the embedding and the heading too
little.

## Sample Chunks

From `python app.py chunks -n 5`, pasted unedited.

**Chunk 1** — source: `guide_accessibility.md#0` — produced by: `chunker.py::split_documents`

```
# Getting around the region with limited mobility

An honest assessment rather than a promotional one. Some of these places are
difficult and it is better to know in advance.
```

**Chunk 2** — source: `guide_corry_vale.md#5` — produced by: `chunker.py::split_documents`

```
# Corry Vale
## Where to stay

Perhaps thirty beds in the entire valley, spread across two pubs and a handful of farmhouse rooms. In summer these are booked months ahead. Camping is permitted on two marked fields and nowhere else.
```

**Chunk 3** — source: `guide_givens_mill.md#2` — produced by: `chunker.py::split_documents`

```
# Givens Mill
## Getting around

Everything is on one street along the river. The mill is at one end and the church at the other, eight minutes apart. The riverside path continues in both directions for as far as you want to walk.
```

**Chunk 4** — source: `guide_kestrelford.md#5` — produced by: `chunker.py::split_documents`

```
# Kestrelford
## Where to stay

Two inns on the square and a handful of rooms above the pubs. Booking ahead matters between May and September and not at all otherwise. There is no accommodation of any kind within four miles of the town in either direction.
```

**Chunk 5** — source: `guide_regional_transport.md#0` — produced by: `chunker.py::split_documents`

```
# Getting around the region
## The railway

The line runs along the river valley, connecting Brightwater to the regional
hub in 50 minutes. Eleven services a day on weekdays, six on Sundays. The line
north of Brightwater closed in 1963 and everything beyond it is bus or car.

Tickets are cheaper booked the day before than on the day, and considerably
cheaper than that booked a week ahead. There is no ticket office at
Brightwater station outside weekday mornings; the machine on the platform takes
cards only.
```

Chunks 2 and 4 are the case for the title prefix. Both are *Where to stay*
sections of almost identical shape, and the only thing separating them is the
`# Corry Vale` and `# Kestrelford` on the front.

**Against criterion 4:** all five begin at a title or a `##` heading, and none
is under 150 characters. Checked across the whole index rather than the
sample — of all 96 chunks, none starts mid-sentence and the shortest is 174.

## Sample Answer

**Question:** Why do visitors get caught out by bus tickets in this region?

**Answer:** from `python app.py ask "..."`, pasted unedited.

```
  (best distance 0.630, cutoff 0.72)

Visitors get caught out because three operators run in the region and they do not accept each other's tickets (guide_regional_transport.md).

Sources retrieved: guide_accessibility.md, guide_eating.md, guide_kestrelford.md, guide_marchwood.md, guide_regional_transport.md

1 model calls this session, 515 tokens (485 in, 30 out)
```

I picked this question because it is the one that made the cutoff matter. At
the starter's default of 0.6 it would have been refused.

**My relevance cutoff:** 0.72

I ran all ten questions through `store.py::search` and recorded the best
distance for each. The two groups do not overlap:

- **In corpus:** 0.2437 to 0.6295
- **Out of corpus:** 0.8026 to 0.9753

The gap runs from **0.6295 to 0.8026** and is 0.17 wide, which is larger than I
expected. I put the cutoff at 0.72, roughly in the middle, leaving about 0.09
of margin on each side. The gate passes a question when the best distance is
*under* the threshold (`gate.py::check`), so 0.72 admits everything in the
first group and refuses everything in the second.

**The default of 0.6 was wrong for this system, and by more than a rounding
error.** Question 3 sits at 0.6295, so the shipped cutoff would have refused a
question the corpus answers in a single sentence. Two things pushed it there:
that question names no town, so it cannot lean on the title prefix the way the
other four do, and my chunking change moved every distance in the corpus.
The 0.6 default was measured against the shipped 800/120 chunking, and
`corpora/README.md` says as much.

Measured at 0.72: **5 of 5 in-corpus questions pass the gate, 5 of 5
out-of-scope questions are refused.**

| Question | In corpus? | Best distance |
|---|---|---|
| What time does the bakery in Kestrelford sell out? | yes | 0.3221 |
| How often do Marchwood's trams run on weekdays? | yes | 0.2437 |
| Why do visitors get caught out by bus tickets in this region? | yes | 0.6295 |
| When does the road to Elder Ness flood? | yes | 0.3368 |
| How long should I allow for the mill museum in Brightwater? | yes | 0.2794 |
| What is the capital of Mongolia? | no | 0.8026 |
| How do I change the oil in a diesel engine? | no | 0.8881 |
| Who won the 1994 World Cup? | no | 0.9753 |
| What is the recommended dosage of ibuprofen for a headache? | no | 0.8350 |
| How do I write a for loop in Rust? | no | 0.8365 |

Two things I got wrong in advance, both worth keeping visible:

**The question I named as the hard one was the second easiest.** In
`criteria.md` I predicted the mill museum question would be the miss, because
`guide_givens_mill.md` is a whole document about a working watermill. It came
back at 0.2794 and the top hit was `guide_brightwater.md#4`, the section that
actually holds "Allow 90 minutes". The word "Brightwater" in the question was
enough, and the title prefix I added in Milestone 3 is what made it decisive.

**I predicted Mongolia would be the out-of-scope question that slipped
through, and it is the closest of the five — but at 0.8026 it is nowhere near
getting through.** The reasoning was right about the ordering and wrong about
the magnitude.

## How I Used AI

**1. The chunker, and the number it picked.** I asked Claude to replace
`split_documents` with something that splits on `##` headings instead of a
character count. What came back did that, and also prefixed every chunk with
the document's `# Title` line, which I had not asked for. I kept the prefix —
it is the thing that separates the nine byte-identical *Practical notes*
sections, and without it a chunk reading "Buses run four times a day" never
says which town it means.

What I did change was the size cap. The version I was handed kept
`CHUNK_SIZE = 800`, and on this corpus that number does nothing at all: I had
it measure the sections first, and the longest is 708 characters, so the cap
would never once have fired. I set it to 600 instead, which splits the two
sections that pack several places into one block — `guide_accessibility.md` →
*Straightforward* covers Thornby Wells, Marchwood and Brightwater in three
paragraphs, and a question about one of them was competing with the other two
inside the same chunk.

**2. Checking an improvement that was reported as a win.** After the chunking
change the summary I got was that retrieval had improved, with the best
distance on my test question dropping from 0.4449 to 0.3674 and four of the
top five hits now coming from the right document. Both numbers are true. I
asked for the same question to be run again at `--top-k 8` to see the whole
ranking, and the *Getting there* section — the one that actually answers "how
do I get to Kestrelford?" — came back **7th**, outside the default top five.
The title prefix that fixed picking the right document had broken picking the
right section inside it, because every chunk from one town now opens with the
same line.

I kept the change and wrote the regression into the Chunking Strategy section
above rather than letting the improvement stand on its own. It is the clearest
thing I have going into unit 2.


**Not doing a stretch feature.** Recording that here so it is explicit.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

From `results/run_2026-09-22_1226_before.md`, produced by `run_eval.py::main`
at top-k 5 and cutoff 0.72, three runs per question with caching off. No
`scorer.py` exists yet, so the script left its verdict columns blank and I
judged all fifteen answers by reading them.

> **I changed one line of starter code to get this run to finish.** The first
> two attempts died partway through on `503 UNAVAILABLE` — the model under
> load, not a rate limit and not my key. `generate.py` already retries with
> backoff, but only for 429 and quota errors, so a 503 raised immediately and
> `run_eval.py` writes its report only after all fifteen calls succeed. Every
> completed call was discarded. I added 503 to the same retry condition.
> The before run then completed, absorbing nine retries across 24 calls, and
> the after run absorbed two across 17. Nothing about retrieval, chunking or
> the answers changed — the same call is simply attempted again when the
> service pushes back.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 2. Every answer names a source | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 4. Chunks start at a heading, none under 150 chars | 5 of 5 sampled, and no chunk in the index under 150 | 96 of 96 | 96 of 96 | 96 of 96 | MET |
| 5. The source named is the right source | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |

**Three of these five cannot vary between runs, and the identical columns are
the honest result rather than a copy-paste.** `README.md` already says this
about criterion 3. It is equally true of criterion 1, which is decided entirely
by retrieval — the same question against the same index returns the same
chunks, and the best distances in the run log are identical to four decimal
places across all three runs. It is true of criterion 4 as well, which is a
property of the index and never reaches the model at all. Only criteria 2 and 5
depend on generation and could have differed; both came out the same three
times anyway.

### Real output

**Criterion 1 — retrieved chunk contains the answer.** Retrieval by
`store.py::search` over chunks from `chunker.py::split_documents`. The
`expects` string from `questions.py` appears in the retrieved chunks for all
five. Best distances, identical in all three runs:

```
0.3221  guide_kestrelford.md#3   What time does the bakery in Kestrelford sell out?
0.2437  guide_marchwood.md#2     How often do Marchwood's trams run on weekdays?
0.6295  guide_kestrelford.md#2   Why do visitors get caught out by bus tickets in this region?
0.3368  guide_elder_ness.md#1    When does the road to Elder Ness flood?
0.2794  guide_brightwater.md#4   How long should I allow for the mill museum in Brightwater?
```

**Criterion 2 — every answer names a source.** Written by
`generate.py::answer_from_chunks`. All fifteen answers named one. Three from
the log, showing the three different formats the model chose:

```
Marchwood's trams run every 8 minutes on weekdays (guide_marchwood.md).
```

```
The bakery in Kestrelford sells out by 11am. 

*(Source: guide_kestrelford.md and guide_eating.md)*
```

```
Marchwood's trams run every 8 minutes on weekdays. 

Source: `guide_marchwood.md`
```

**Criterion 3 — the gate stops out-of-corpus questions.** Produced by
`run_eval.py::check_out_of_scope`, one deterministic pass:

```
  refused  (best distance 0.803)  What is the capital of Mongolia?
  refused  (best distance 0.888)  How do I change the oil in a diesel engine?
  refused  (best distance 0.975)  Who won the 1994 World Cup?
  refused  (best distance 0.835)  What is the recommended dosage of ibuprofen for a headache?
  refused  (best distance 0.836)  How do I write a for loop in Rust?
  -> gate refused 5 of 5
```

**Criterion 4 — chunks start at a heading, none under 150 characters.** Not
something `run_eval.py` measures, so this is checked directly against
`chunker.py::split_documents`:

```
total 96
not starting at a heading: none
shorter than 150: none
```

And from `python app.py index`:

```
  chunked  96 chunks, 315 characters on average (shortest 174, longest 610), produced by chunker.py::split_documents
```

**Criterion 5 — the source named is the right source.** Judged by reading each
answer against the document it cites. All five name a document that genuinely
contains the fact. The one I expected to fail:

```
You should allow 90 minutes for the mill museum in Brightwater (guide_brightwater.md).
```

`guide_givens_mill.md` was retrieved for this question — it is in the sources
list for all three runs — and the model cited `guide_brightwater.md` anyway,
which is the file holding "Allow 90 minutes". Question 1 cites two documents,
`guide_kestrelford.md` and `guide_eating.md`, and both really do carry the 11am
line, so I counted it correct rather than penalising the extra citation.

## Verdicts

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunks contain the answer | **MET** | Searched the retrieved chunks for the `expects` string I wrote in `questions.py` at Milestone 2, before any of this ran. Present for all five. Not close: the target was 4 of 5. |
| 2 | Every answer names a source | **MET** | Read all fifteen answers. Every one names a document. I counted a source as named in whatever format the model chose — `(guide_marchwood.md)`, a `Source:` line, a backticked filename — since the criterion asks whether a source is named, not how. |
| 3 | The gate stops out-of-corpus questions | **MET** | From the gate table. All five refused, and the closest, Mongolia at 0.803, sits 0.083 above the 0.72 cutoff. Nothing near the line. |
| 4 | Chunks start at a heading, none under 150 chars | **MET** | Checked all 96 chunks rather than the 5 I sampled, since the criterion claims something about the index. None starts mid-sentence; the shortest is 174. **The tightest of the five** — 24 characters of margin on a 150 floor. |
| 5 | The source named is the right source | **MET** | Read each answer against the document it cites and confirmed that document contains the stated fact. One judgment call: question 1 cites two documents, `guide_kestrelford.md` and `guide_eating.md`. Both genuinely carry the 11am line, so I counted it correct. Had either been wrong I would have scored it a miss, since the criterion is about the source being right. |

## Diagnoses

**I missed nothing. All five criteria are MET, and four of the five came in at
5 of 5 against targets of 4 of 5.** So this section is the other thing that
question asks for: whether the targets were set low, and what is broken anyway.

### The targets were set low, and I can say exactly why

Three of them were set at 4 of 5 for reasons that turned out to be wrong.

**Criterion 1** was 4 of 5 because I predicted in `criteria.md` that the mill
museum question would fail — `guide_givens_mill.md` is a whole document about a
working watermill, and I expected it to win on the word "mill". It came back at
0.2794, the second-closest distance of the five, and the model cited
`guide_brightwater.md` correctly all three runs. I built in a failure that did
not happen. It should have been 5 of 5.

**Criterion 3** was 4 of 5 in case the Mongolia question slipped through, since
the corpus is full of place-and-population language. It is the closest of the
five out-of-scope questions, which was the right call, but at 0.803 against a
0.72 cutoff it is not remotely close to passing. The measured gap between the
two groups is 0.17 wide. It should have been 5 of 5.

**Criterion 5** was 4 of 5 for the same mill-museum reason as criterion 1, and
is wrong for the same reason.

**Criterion 4 is the one I would leave alone.** It is the only criterion with a
real margin worth reporting rather than a wide one: the shortest chunk in the
index is 174 against a floor of 150. It is also the only one that would have
failed before Milestone 3, when the shortest chunk was 24 characters.

### What is broken anyway: my test set cannot see the defect I already found

Passing everything does not mean the system works. In Milestone 3 I recorded
that the *Getting there* section of `guide_kestrelford.md` had fallen to 7th
for *"how do I get to Kestrelford?"*, outside the default top-k of 5. That is
still true, and I measured how far it spreads:

| Town | Rank of its own *Getting there* section |
|---|---|
| Halden Bay | 1 |
| Brightwater | 3 |
| Thornby Wells | 3 |
| Elder Ness | 7 |
| Kestrelford | 7 |
| Marchwood | 9 |
| Corry Vale | 9 |
| Pellew Sands | 9 |
| Givens Mill | 13 |

**For 6 of the 9 towns, the section that answers "how do I get there" is not
retrieved at all at `TOP_K = 5`.** This is not one unlucky question.

**Stage: chunking, showing up in retrieval.** The decision is in
`chunker.py::split_documents`; the symptom appears in `store.py::search`. The
mechanism: every chunk from one town now opens with the same `# Kestrelford`
line, and chunks average 315 characters, so that shared prefix is a large
fraction of each one. For a query like "how do I get to Kestrelford?", the town
name is the only strong signal in the question — "get to" is generic — so all
eight Kestrelford chunks score alike on the part that matters, and the thing
that should separate them, the `## Getting there` heading, is one short line
against 250 characters of body text about pubs and inns. *Where to stay* wins
because its body is longer, not because it is more relevant.

This is the cost of the fix that made criterion 5 pass. The title prefix is
what stops the nine byte-identical *Practical notes* sections being
indistinguishable, and it is what let the model cite `guide_brightwater.md`
over `guide_givens_mill.md`. The same prefix is what flattens the sections
within a town. One change, helping one criterion and breaking something no
criterion measures.

**Why none of my five questions catches it.** Four of them pair a place with a
distinctive content word — bakery, trams, flood, museum — and each of those
words appears in the body of exactly one section, so the body does the
discriminating and the title prefix only helps. The fifth names no town at all.
Not one has the shape that breaks: a generic verb plus a town name, where the
title is the only thing the query has to go on. I wrote five questions that the
title prefix was guaranteed to help, before I had written the title prefix.

## The Improvement

**What I changed:** The chunk header went from two markdown lines to one, and
the retrieval window widened from 5 to 8.

```
                 before                      after

                 # Kestrelford               Kestrelford — Getting there
                 ## Getting there
                                             No railway station; the line
                 No railway station; the     was closed in 1963 ...
                 line was closed in 1963 ...
```

`chunker.py::split_documents` now writes `Kestrelford — Getting there` as a
single line with the `#` markers dropped, and `TOP_K` in `config.py` is 8.

**Why I picked it:** The diagnosis above says the title prefix flattens every
section within a town, because the shared `# Kestrelford` line is a large
share of a 313-character chunk while the `## Getting there` heading that
should separate them is one short line — so this puts the two on the same
line, at the same weight, with the markdown noise gone.

The two parts are one fix rather than two, and the measurements are why. I
tested three header formats as separate index variants before changing
anything, using the `--variant` support in `store.py::build_index`, and
scored each one on the diagnosis's own metric — the rank of each town's own
*Getting there* section for "how do I get to X?":

| Header format | Ranks across the 9 towns | Worst | Inside top-5 |
|---|---|---|---|
| `# Town` / `## Heading` (before) | 3, 7, 1, 9, 9, 7, 13, 9, 3 | 13 | 3 of 9 |
| **`Town — Heading` (chosen)** | 1, 6, 1, 7, 7, 7, 7, 8, 2 | **8** | 3 of 9 |
| `Heading — Town. Heading.` | 6, 7, 1, 8, 12, 6, 16, 9, 5 | 16 | 2 of 9 |

Reformatting alone moves the worst rank from 13 to 8 and leaves the headline
number unchanged at 3 of 9 — every correct chunk is now within reach of a
window of 8, and none of them is inside a window of 5. Widening alone, without
the reformat, would have had to reach 13 to catch every town. Doing both is
what makes the correct section retrievable; doing either is not. I have
reported them as one change because one diagnosis produced both and neither
stands up without the other.

Doubling the heading, the third row, made things worse, which is the reason I
tested rather than reasoned.

**Measured after the change**, at `TOP_K = 8`:

```
TOP_K=8: Getting there in window for 9/9
{'Brightwater': 1, 'Kestrelford': 6, 'Halden Bay': 1, 'Marchwood': 8,
 'Corry Vale': 8, 'Elder Ness': 7, 'Givens Mill': 7, 'Pellew Sands': 8,
 'Thornby Wells': 2}
```

**It also fixed a mis-attribution none of my five questions tests.** Asked
*"what is mobile coverage like in Marchwood?"* — a question landing squarely
on the *Practical notes* paragraph that nine documents share — the old index
returned `guide_eating.md`. The new one returns `guide_marchwood.md`. That is
criterion 5 failing in a way my run log scored 5 of 5 on.

### Run Log — After

From `results/run_2026-09-22_1302_after.md`, same five criteria, three runs
each, at top-k 8 and cutoff 0.72. Judged the same way as before, by reading
all fifteen answers.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 2. Every answer names a source | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 4. Chunks start at a heading, none under 150 chars | 5 of 5 sampled, and no chunk in the index under 150 | 96 of 96 | 96 of 96 | 96 of 96 | MET |
| 5. The source named is the right source | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |

**Did it help?**

**Yes, and the run log cannot show it.** The after table is identical to the
before table — five criteria, all MET, all at 5 of 5. Nothing moved, because
there was nowhere for it to move to. Every criterion was already at ceiling
before I changed anything.

What did move is the thing the diagnosis was about, measured the same way
before and after:

| | before | after |
|---|---|---|
| *Getting there* inside the retrieval window, across 9 towns | **3 of 9** | **9 of 9** |
| Worst rank for that section | 13th | 8th |
| *"mobile coverage in Marchwood?"* cites | `guide_eating.md` | `guide_marchwood.md` |

Six towns went from having the section that answers "how do I get there" not
retrieved at all, to having it retrieved every time. That is the fix working.
It earns nothing in the run log because not one of my five test questions asks
a question of that shape.

**The honest summary is that I fixed a real bug and proved it with a
measurement I had to invent, because the acceptance criteria I wrote in unit 1
are not sensitive to it.** The criteria are not wrong, and I have not revised
them — they measure real things and all five still hold. They are just
incomplete in a way I could not see until I had results.

**What I watched for and did not find.** Going from 5 to 8 chunks means the
model sees more material it does not need, and my worry was that criterion 5
would slip — more retrieved documents, more chances to cite one that merely
came along. The opposite happened. The model now cites *more* documents, and
every one of them is correct:

- Question 2 cites `guide_marchwood.md` and `guide_accessibility.md`. Both
  contain "every 8 minutes".
- Question 4 cites `guide_elder_ness.md` and `guide_walking.md`. Both describe
  the road flooding at the highest spring tides, six times a year. The answer
  even adopts `guide_walking.md`'s phrase "single access road", so it is
  genuinely using the second document rather than listing it.

**One thing got slightly worse.** Two of the five in-corpus distances moved the
wrong way — question 1 from 0.3221 to 0.3413, and question 3 from 0.6295 to
0.6372. Question 3 is the one nearest the 0.72 cutoff, so its margin narrowed
from 0.090 to 0.083. Three others improved, the largest being question 4 at
0.3368 to 0.2666. The out-of-corpus group stayed where it was, closest still
Mongolia at 0.808. The gap is intact and nothing is near the line, but the
change did not make every number better and it would be wrong to present it
as though it had.

## What's Still Broken

No criterion is still missed, because none was missed to begin with. What
follows is what is broken anyway.

**The corpus contradicts itself and the system has no way to notice.** Nine
town guides end with the same paragraph saying the nearest full hospital is in
Brightwater. `guide_accessibility.md` says it is in Marchwood. Asking *"is
there a hospital near Marchwood?"* retrieves both, ranked one and two:

```
0.2730  guide_accessibility.md#5   ... The nearest full hospital is in Marchwood ...
0.3477  guide_marchwood.md#7       Marchwood — Practical notes ... nearest full hospital is in Brightwater ...
```

Two chunks in the same prompt asserting opposite things, and whichever the
model picks, it will name a real source and sound confident. Criterion 5 passes
either way, because the document it cites does contain the sentence it used. I
would want a criterion about answers being *consistent with the corpus* rather
than merely sourced from it, and a retrieval step that can flag when two
retrieved chunks disagree. I did not attempt it because I only found the
contradiction while reading documents in Milestone 1, wrote it down as the
reason for criterion 5, and did not realise until now that criterion 5 does not
actually catch it.

**Widening the window is a workaround, not a ranking fix.** The correct chunk
is retrieved for all nine towns now, but for six of them it is still ranked
below sections that answer a different question. I am paying for that in every
prompt: input tokens per answer went from about 521 to about 768, a 47%
increase, for material the model mostly does not need. The real fix is making
the heading count for more at ranking time — hybrid search with `rank-bm25`,
which ships with the starter, would let an exact match on "getting there" carry
weight that a dense embedding spreads thin. I stopped because that is a second
change, and the unit asks for one change I can actually attribute.

> **Followed up as the stretch feature.** I built it after writing this, and
> it took the worst rank from 8 to 6 and let `TOP_K` come back to 6, recovering
> about half of that 47%. It did not fix the ranking properly — the correct
> section still is not in the top 3 for six of nine towns. See Stretch
> Feature — Hybrid Search at the end.

**Everything is judged by me reading it.** There is no `scorer.py`, so all
thirty answers across both runs were scored by my own reading, and the
"5 of 5" in both tables is my judgment rather than a measurement. Two places
where a different reader could reasonably disagree: whether an answer citing
two documents counts as correct when both are right, and whether a source named
as `` `guide_marchwood.md` `` in a sentence counts the same as a `Source:`
line. I wrote down how I decided each one so at least the judgment is visible.

**A known hole in `expects` that I recorded before it mattered.** Question 1
expects the substring `11am`, and `guide_givens_mill.md` also says a car park
fills by 11am. A scorer built on substring matching would pass an answer about
the wrong village. It did not happen in either run, but the check is weaker
than the table makes it look. The comment is in `questions.py` from Milestone 2.

## What I'd Do Differently

**Criterion 1, and it is not about the number.** As written it asks whether
the retrieved chunks *include* one containing the answer. That is satisfiable
by retrieving more chunks — and raising `TOP_K` from 5 to 8 is literally half
of the fix I shipped this unit. My own improvement made criterion 1 easier to
pass without making the ranking better, and the criterion cannot tell the
difference. I would rewrite it about **position**, not membership:

> For at least 4 of my 5 test questions, a chunk containing the answer is in
> the top 3 results.

That version would have failed in unit 1, which is the point. It would have
caught the title-prefix problem in Milestone 3 instead of leaving me to find it
by accident, and no amount of widening the window would make it pass.

**The targets on criteria 1, 3 and 5 should all have been 5 of 5.** All three
were set at 4 of 5 to leave room for failures I predicted and did not get: the
mill museum question on 1 and 5, the Mongolia question on 3. Diagnosed at
length in Diagnoses above. Setting a target that leaves room for a failure you
have imagined is not the same as setting one you might miss.

**Criterion 4 should describe the property, not the format.** I wrote "begins
at a document title or a `##` section heading". Then in unit 2 I removed the
`##` markers, and the criterion's wording no longer matched the thing it was
protecting, even though the property held perfectly — I had to rewrite the
check to validate header lines against the real titles and headings. The
criterion should have said *no chunk begins mid-sentence*, which is what I
actually cared about and would have survived the change.

**The question set, more than any single criterion.** Four of my five questions
pair a place with a distinctive word — bakery, trams, flood, museum — and the
fifth names no place at all. Every one of them is a question the title prefix
was guaranteed to help, and I wrote them before I had written the title prefix,
which is luck rather than design. Missing entirely: a question where the place
name is the only strong signal and the section topic has to do the
discriminating, which is the exact shape that fails for six of nine towns. One
question of the form "how do I get to X?" would have turned a unit of
everything-passes into a unit with a real miss to diagnose.

**On the whole thing.** The run log says 5 of 5 on every criterion in both
runs, and the system had a retrieval bug affecting two thirds of the towns in
the corpus the entire time. That gap between what my tests said and what was
true is the thing I would most want to avoid repeating.

---

## Stretch Feature — Hybrid Search

> **Declared before starting, and not implemented at this commit.** Unit 1 says
> I was not doing a stretch feature, and at that point I was not. This is a
> unit 2 decision and the line above it stays as it was written.

**What I am adding:** BM25 keyword scoring alongside the existing dense vector
search in `store.py::search`, with the two rankings fused into one. The
`rank-bm25` package already ships with the starter.

**Why this one.** It is the fix my own Diagnoses section named and then put
down. The diagnosis is that the section heading is under-weighted: for "how do
I get to Kestrelford?" every chunk from that town scores alike on the dense
embedding, and `## Getting there` is one short line that the embedding spreads
thin. BM25 scores exact term overlap, so the literal words "getting there" in
the header should count for something the dense model is averaging away.

**What I expect, written down before I measure it.** The one-line header and
`TOP_K = 8` got the correct section inside the window for 9 of 9 towns, but
for six of them it is still ranked below sections answering a different
question, and I am paying about 47% more input tokens per answer to carry
chunks the model does not need. If BM25 does what I think, the correct section
should move into the **top 3** for most towns, and I should be able to put
`TOP_K` back to 5 and keep the fix.

**How I will judge it:** the same nine-town probe used throughout unit 2,
before and after, plus a check that criteria 1 to 5 do not regress. If it does
not help, that goes here too.

### What I built

`store.py::search` now retrieves the dense way and the BM25 way and fuses the
two rankings in `store.py::_fuse`, using reciprocal rank fusion: each chunk
scores `1/(k + rank)` in each ranking and the two are added, with the BM25 side
weighted by `config.BM25_WEIGHT`. Ranks are fused rather than raw scores,
because a cosine distance and a BM25 score are not on the same scale.

**`Result.distance` is still the true cosine distance.** This was the one
design constraint I would not bend: `gate.py::check` compares that number
against `config.THRESHOLD`, and the 0.72 I measured in Milestone 4 describes
cosine distances. Putting a fused score there would have silently invalidated
the cutoff, criterion 3, and every distance in this README. Hybrid changes the
*order* of results, not what a distance means.

### The first attempt made it worse

Plain BM25 over lowercased words moved the Kestrelford *Getting there* section
**out of the top 8 entirely**. The reason is in one line of output:

```
query tokens: ['how', 'do', 'i', 'get', 'to', 'kestrelford']
target bm25 rank: 34
top by BM25 alone: 5.318  guide_pellew_sands.md#5  Pellew Sands — Where to stay
```

The question says **get** and the header says **Getting**, and BM25 matches
tokens exactly, so the single word that was supposed to connect them never
did. Meanwhile "how", "do", "to" matched nearly everywhere, and BM25's length
normalisation handed the top spot to a short chunk about a different village.
The keyword half was contributing noise.

So `store.py::_tokenize` drops stopwords and strips suffixes — crude, about
fifteen lines, and not a real stemmer, but enough that `getting` and `get`
become the same token. The query reduces to `['get', 'kestrelford']` and the
target's BM25 rank goes **34 → 3**.

### Did it help? Partly, and less than I predicted

| Rank of each town's own *Getting there* section | dense only | hybrid, tuned |
|---|---|---|
| Ranks across the nine towns | 1, 6, 1, 8, 8, 7, 7, 8, 2 | 5, 3, 3, 6, 6, 4, 3, 5, 3 |
| Inside top 3 | 3 of 9 | **3 of 9** |
| Inside top 5 | 3 of 9 | **7 of 9** |
| Worst rank | 8 | **6** |

**I predicted the correct section would reach the top 3 for most towns. It did
not — that number did not move at all.** What moved is everything below it:
top-5 coverage more than doubled and the worst case came in from 8th to 6th.

The mechanism is visible in the individual ranks. Hybrid compresses the
distribution from both ends. Towns the dense model already got right got
slightly worse — Brightwater 1st to 5th, Halden Bay 1st to 3rd — and the ones
it got badly wrong improved. BM25 is adding a signal that is broadly right and
rarely precise.

**What that bought, concretely:** `TOP_K` comes down from 8 to 6 and the
correct section is still retrieved for 9 of 9 towns. That is a quarter fewer
chunks in every prompt, so roughly half of the 47% token overhead from The
Improvement is recovered. My prediction of getting back to 5 was too
optimistic: at `TOP_K = 5` two towns still lose their section.

**No regression.** At both `TOP_K = 6` and `TOP_K = 8`: criterion 1 at 5 of 5,
all five in-corpus questions pass the gate, all five out-of-scope questions
refused, and *"mobile coverage in Marchwood?"* still cites
`guide_marchwood.md`.

### The caveat that matters

**`BM25_WEIGHT = 2.0` was chosen by sweeping it against the same nine-town
probe I then used to declare success.** I tried weights from 0 to 10 and picked
the one with the lowest worst-case rank. That is tuning on the test, and the
7 of 9 should be read as optimistic — it is the best this corpus gives up, not
a number I would expect to hold on questions I have not tried. Doing it
honestly would mean a second set of probe questions, held back and looked at
once. I did not have one, and inventing it after seeing these results would
not have made it held back.
