"""
Your test questions.

Milestone 2 asks you to write five questions your system should be able to
answer from your corpus, specific enough to have a right answer.

  ✗ "What are good dining halls?"          — no right answer
  ✓ "What do students say about wait times at Commons during lunch?"

Fill in `QUESTIONS` below. `expects` is a word or short phrase you'd expect a
correct answer to contain — you'll use it in unit 2 when you build a scorer,
and having written it now means you decided what "correct" meant before you saw
any results.

`OUT_OF_SCOPE` holds five questions your documents clearly don't cover. You
need these in Milestone 4 to find where your relevance cutoff belongs, and
again in unit 2, where `run_eval.py` runs them through the gate and writes what
happened into your run log — that's the evidence for criterion 3.

Swap them for your own if you like. Keep five of them either way: criterion 3
names a target of "4 of 5", and four of three is not a thing.
"""

QUESTIONS = [
    # Answer sits in one sentence, and two documents carry it
    # (guide_kestrelford.md "Eat and drink", guide_eating.md "Local specifics").
    # Known weakness: "11am" also appears in guide_givens_mill.md, about a car
    # park filling up. A substring scorer will pass an answer about the wrong
    # place.
    {"question": "What time does the bakery in Kestrelford sell out?", "expects": "11am"},
    # Same fact in guide_marchwood.md "Getting around" and
    # guide_accessibility.md "Straightforward".
    {"question": "How often do Marchwood's trams run on weekdays?", "expects": "8 minutes"},
    # One sentence in guide_regional_transport.md "Buses", nowhere else.
    {"question": "Why do visitors get caught out by bus tickets in this region?",
     "expects": "each other's tickets"},
    # One sentence in guide_elder_ness.md "Getting there", nowhere else.
    {"question": "When does the road to Elder Ness flood?", "expects": "spring tides"},
    # The hard one. Two words inside guide_brightwater.md "What to see", a section
    # that also covers the river walk and the cathedral. "Mill" additionally names
    # a whole other document about a different place.
    {"question": "How long should I allow for the mill museum in Brightwater?",
     "expects": "90 minutes"},
]

# Questions from a different world entirely. Your gate should refuse all five.
#
# There are five of these because criterion 3 in criteria.md names a target of
# "at least 4 of 5" — you need five things to try before you can report 4 of 5.
# `run_eval.py` runs these through retrieval and the gate on every eval and
# records what happened, so criterion 3 has evidence in the run log alongside
# the others. They cost no model calls: a refusal never reaches the model.
OUT_OF_SCOPE = [
    "What is the capital of Mongolia?",
    "How do I change the oil in a diesel engine?",
    "Who won the 1994 World Cup?",
    "What is the recommended dosage of ibuprofen for a headache?",
    "How do I write a for loop in Rust?",
]


def answered() -> list[dict]:
    """The questions you've actually filled in."""
    return [q for q in QUESTIONS if q.get("question", "").strip()]
