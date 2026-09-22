"""
Stage 2 of the pipeline: splitting documents into chunks.

⚠️ THIS IS THE FILE YOU CHANGE IN MILESTONE 3.

`split_documents` below is deliberately plain. It cuts every document into
fixed-size pieces with a fixed overlap and pays no attention to where sentences
or paragraphs end. It works, and it is not good.

On a corpus of short posts it may not cut anything at all: `campus_life` comes
out as 88 documents and 88 chunks, because almost nothing in it reaches 800
characters. That is the baseline, not a bug — Milestone 3 is where you decide
whether one post should stay one chunk.

Your job in Milestone 3 is to replace the *body* of `split_documents` with a
strategy that fits the documents you actually read in Milestone 1. Keep the
name and the shape of what it returns — the rest of the pipeline calls it, and
your README has to name the function that produced your chunks.

If you get stuck for 30 minutes, `fallback_split` is the original. Switch back
to it, write down what you saw, and move on. That's a real observation about
your pipeline, not giving up.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document

# A chunk shorter than this is a heading with nothing under it. Those get
# folded into the chunk before them.
MIN_CHUNK = 150

SECTION_HEADING = re.compile(r"^##\s+.*$", re.M)


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def document_title(text: str) -> str:
    """The `# Title` line, or "" if the document doesn't open with one."""
    first = text.lstrip().split("\n", 1)[0].strip()
    return first if first.startswith("# ") else ""


def sections(text: str) -> list[tuple[str, str]]:
    """
    Split a document into (heading, body) pairs at its `##` lines.

    The first pair has an empty heading and holds everything above the first
    `##` — the title line and, in the town guides, an opening paragraph.
    """
    marks = list(SECTION_HEADING.finditer(text))
    if not marks:
        return [("", text.strip())]

    pairs = [("", text[: marks[0].start()].strip())]
    for i, mark in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        pairs.append((mark.group().strip(), text[mark.end() : end].strip()))
    return pairs


def paragraph_groups(body: str, cap: int) -> list[str]:
    """Break a section at blank lines so each piece stays under `cap`."""
    if len(body) <= cap:
        return [body]

    groups: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        joined = f"{current}\n\n{para}" if current else para
        if current and len(joined) > cap:
            groups.append(current)
            current = para
        else:
            current = joined
    if current:
        groups.append(current)
    return groups


def absorb_short(pieces: list[str]) -> list[str]:
    """Fold anything under MIN_CHUNK into the piece before it."""
    out: list[str] = []
    for piece in pieces:
        if out and len(piece) < MIN_CHUNK:
            out[-1] = f"{out[-1]}\n\n{piece}"
        else:
            out.append(piece)
    return out


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    Split each guide at its `##` section headings, one chunk per section.

    Every document in city_guides is a title followed by labelled sections —
    Getting there, Getting around, Eat and drink, and so on — and each section
    is one self-contained topic averaging 291 characters. The heading is where
    the subject changes, so it is the boundary worth cutting on.

    Two things every chunk carries:

    - The document title, prefixed onto the text. A section body says "Buses
      run four times a day" without ever naming the town, so the title is what
      makes the chunk answerable on its own. It also separates the "Practical
      notes" section, which is byte-identical across all nine town guides.
    - The section heading, which tells the embedding what kind of question the
      chunk answers.

    Sections over CHUNK_SIZE are broken at blank lines. Nothing under
    MIN_CHUNK survives as its own chunk.
    """
    cap = config.CHUNK_SIZE
    chunks: list[Chunk] = []

    for doc in documents:
        title = document_title(doc.text)
        pieces: list[str] = []

        lead_body = sections(doc.text)[0][1]
        intro = lead_body[len(title) :].strip() if title else lead_body
        if intro:
            pieces.append(f"{title}\n\n{intro}" if title else intro)

        for heading, body in sections(doc.text)[1:]:
            if not body:
                continue
            header = "\n".join(part for part in (title, heading) if part)
            for group in paragraph_groups(body, cap):
                pieces.append(f"{header}\n\n{group}" if header else group)

        for index, text in enumerate(absorb_short(pieces)):
            chunks.append(
                Chunk(
                    text=text,
                    source=doc.source,
                    index=index,
                    produced_by="chunker.py::split_documents",
                )
            )

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
