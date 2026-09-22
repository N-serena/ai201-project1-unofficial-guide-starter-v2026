# The Unofficial Guide

<!-- Replace this line with your name and which corpus you picked. -->

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

<!-- Three or four sentences. Which corpus you picked, and the kinds of
     questions your system answers. Write it for someone who has never seen
     this repo.

     Milestone 5. -->

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

<!-- One complete question and answer, pasted as text, with the source line
     visible. Milestone 4. -->

**Question:**

**Answer:**

```
```

**My relevance cutoff:**

<!-- The number you set in config.py, and how you got there.

     You ran five questions your corpus covers and the five in OUT_OF_SCOPE
     that it clearly doesn't, and wrote down the best distance for each. What
     did those two groups look like? Where was the gap? Put the actual numbers
     here — the table below wants all ten rows.

     Milestone 4. -->

| Question | In corpus? | Best distance |
|---|---|---|
|  |  |  |

## How I Used AI

<!-- Two specific moments. For each: what you asked for, what came back, and
     what you changed about it.

     "I asked Claude to write the chunking function from my notes. It ignored
     the overlap, so I added that myself" is the level of detail we're after.
     "I used AI to help me code" is not.

     Milestone 5. -->

**1.**

**2.**

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
