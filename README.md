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

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. | | | | | |
| 5. | | | | | |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
