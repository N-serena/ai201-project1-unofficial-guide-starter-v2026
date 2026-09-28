"""
Stages 3 and 4 of the pipeline: embedding chunks and retrieving them.

Three things in here are worth knowing about, because they'd quietly break the
rest of the project if they were wrong:

1. The Chroma collection is created with cosine distance, explicitly. Chroma
   defaults to squared L2, and the 0.6 threshold the course uses is calibrated
   against cosine. Getting this wrong makes every distance number meaningless.

2. `search` returns the distance alongside each chunk. Milestone 4 has you
   compare distances, so they have to be visible.

3. The embedding model is the one Chroma bundles, not one loaded through
   `sentence-transformers`. It is the same model — `all-MiniLM-L6-v2`, 384
   dimensions — but it arrives as an ONNX build from Chroma's own CDN, so the
   install needs neither PyTorch nor a reachable Hugging Face. See `_embedder`.
"""

import os
import re
import shutil
from dataclasses import dataclass

# Must be set BEFORE chromadb is imported. Without it, some Chroma versions
# print "Failed to send telemetry event ..." on every single call — which looks
# exactly like a real error, isn't one, and cost a previous cohort a lot of
# confused help-channel messages.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

import chromadb  # noqa: E402

import config
from chunker import Chunk


@dataclass
class Result:
    """One retrieved chunk and how far it was from the question."""

    text: str
    source: str
    label: str
    distance: float   # LOWER IS BETTER. 0.3 is close, 0.9 is unrelated.
    produced_by: str


_model = None

# The model Chroma bundles. Anything else in config.EMBEDDING_MODEL means
# "fetch that one from Hugging Face instead" — see `_embedder`.
BUNDLED_MODEL = "all-MiniLM-L6-v2"


class _OnnxEmbedder:
    """
    Chroma's built-in embedder, wrapped to look like the other two.

    Chroma's embedding functions are called directly and hand back numpy
    arrays. The rest of this file wants `.encode(texts)`, so the adapter lives
    here rather than making every caller care which embedder it got.
    """

    def __init__(self):
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

        self._ef = ONNXMiniLM_L6_V2()

    def encode(self, texts, show_progress_bar: bool = False):
        return [vector.tolist() for vector in self._ef(list(texts))]


def _sentence_transformer(name: str):
    """
    The escape hatch: any model that isn't the bundled one.

    Unit 2's "try a second embedding model" stretch option comes through here,
    and so does anything you set `EMBEDDING_MODEL` to. This path *does* need
    `sentence-transformers` and a reachable Hugging Face, neither of which the
    default install has — which is the whole point of the default install.
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            f"config.EMBEDDING_MODEL is set to {name!r}, which isn't the model "
            f"Chroma bundles ({BUNDLED_MODEL!r}), so it has to be downloaded "
            f"from Hugging Face.\n"
            f"Install the optional dependency first:\n"
            f"    pip install 'sentence-transformers>=3.4,<3.5'\n"
            f"Or set EMBEDDING_MODEL back to {BUNDLED_MODEL!r}."
        ) from exc

    return SentenceTransformer(name)


def _embedder():
    """
    Load the embedding model once and keep it.

    First call is slow — it downloads about 80 MB. That's why setup happens
    before class.
    """
    global _model

    if _model is not None:
        return _model

    # Used only by this repo's own smoke test, which runs where no model can be
    # downloaded at all. Never set this yourself.
    if os.getenv("AI201_FAKE_EMBEDDINGS") == "1":
        from _smoke_embedder import FakeEmbedder

        _model = FakeEmbedder()
    elif config.EMBEDDING_MODEL == BUNDLED_MODEL:
        _model = _OnnxEmbedder()
    else:
        _model = _sentence_transformer(config.EMBEDDING_MODEL)

    return _model


def embed(texts: list[str]) -> list[list[float]]:
    """Turn text into vectors. Runs on your machine, costs no API quota."""
    vectors = _embedder().encode(texts, show_progress_bar=False)
    # sentence-transformers and the smoke stand-in return something with a
    # .tolist(); _OnnxEmbedder has already done that conversion itself.
    return vectors.tolist() if hasattr(vectors, "tolist") else vectors


def _client():
    return chromadb.PersistentClient(
        path=str(config.CHROMA_DIR),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_index(
    chunks: list[Chunk],
    corpus: str | None = None,
    variant: str = "default",
) -> int:
    """
    Embed every chunk and store it.

    `variant` lets you keep more than one index of the same corpus at the same
    time. In unit 2, when you compare two chunking strategies, index the second
    one as variant="v2" and you can query both instead of deleting the first
    and starting over.
    """
    name = config.collection_name(corpus, variant)
    client = _client()

    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        # ⚠️ Do not remove. Chroma defaults to squared L2, and every distance
        # number in this course assumes cosine.
        metadata={"hnsw:space": "cosine"},
    )

    batch = 256
    for start in range(0, len(chunks), batch):
        window = chunks[start : start + batch]
        collection.add(
            ids=[f"{c.source}#{c.index}" for c in window],
            documents=[c.text for c in window],
            embeddings=embed([c.text for c in window]),
            metadatas=[
                {"source": c.source, "index": c.index, "produced_by": c.produced_by}
                for c in window
            ],
        )

    return len(chunks)


_bm25_cache: dict[str, tuple] = {}


# Words that appear in nearly every chunk and in nearly every question. BM25
# still scores them, and with short chunks that noise decides the ranking.
_STOPWORDS = frozenset("""
a an and are as at be been by can do does for from had has have how i if in into
is it its me my no not of on or our should than that the their them then there
these they this to was were what when where which who why will with would you your
""".split())


def _stem(word: str) -> str:
    """
    A crude suffix stripper, not a real stemmer.

    It exists for one reason: the question says "get" and the header says
    "Getting", and BM25 matches tokens exactly, so without this the one word
    that should connect them never does.
    """
    for suffix in ("ing", "ed", "es", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            word = word[: -len(suffix)]
            # "getting" -> "gett" -> "get"
            if len(word) > 3 and word[-1] == word[-2]:
                word = word[:-1]
            return word
    return word


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric runs, stopwords dropped, suffixes stripped."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if w not in _STOPWORDS]


def _bm25_for(collection):
    """
    A BM25 index over every chunk in a collection, built once and reused.

    Keyed on the collection's size, so re-indexing invalidates it.
    """
    from rank_bm25 import BM25Okapi

    count = collection.count()
    cached = _bm25_cache.get(collection.name)
    if cached and cached[0] == count:
        return cached[1], cached[2]

    got = collection.get(include=["documents"])
    ids, docs = got["ids"], got["documents"]
    index = BM25Okapi([_tokenize(d) for d in docs])
    _bm25_cache[collection.name] = (count, index, ids)
    return index, ids


def search(
    question: str,
    top_k: int | None = None,
    corpus: str | None = None,
    variant: str = "default",
) -> list[Result]:
    """
    Retrieve the chunks most relevant to a question.

    Returns them best-first, each carrying its cosine distance.

    With config.HYBRID on, the order comes from fusing two rankings: the dense
    vector one and a BM25 keyword one. `distance` stays the true cosine
    distance either way, because the relevance gate compares it against
    config.THRESHOLD and a fused score would make that number meaningless.
    """
    top_k = top_k or config.TOP_K
    name = config.collection_name(corpus, variant)

    try:
        collection = _client().get_collection(name)
    except Exception as exc:
        raise RuntimeError(
            f"No index called '{name}'. Run `python app.py index` first."
        ) from exc

    total = collection.count()
    if not total:
        return []

    # Hybrid needs a distance for anything BM25 might promote, so it scores the
    # whole collection. Fine at this size; a big corpus would want a capped
    # candidate pool instead.
    wanted = total if config.HYBRID else top_k

    raw = collection.query(
        query_embeddings=embed([question]),
        n_results=min(wanted, total),
    )

    results: list[Result] = []
    for text, meta, distance in zip(
        raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
    ):
        results.append(
            Result(
                text=text,
                source=str(meta.get("source", "unknown")),
                label=f"{meta.get('source', 'unknown')}#{meta.get('index', 0)}",
                distance=float(distance),
                produced_by=str(meta.get("produced_by", "unknown")),
            )
        )

    if not config.HYBRID:
        return results

    return _fuse(question, results, raw["ids"][0], collection)[:top_k]


def _fuse(question, results, ids, collection) -> list[Result]:
    """
    Reciprocal rank fusion of the dense ranking and a BM25 ranking.

    Each chunk scores 1/(k + rank) in each ranking and the two are added, the
    BM25 side weighted by config.BM25_WEIGHT. Rank is used rather than the raw
    scores because a cosine distance and a BM25 score are not on one scale.
    """
    index, bm_ids = _bm25_for(collection)
    scores = index.get_scores(_tokenize(question))

    order = sorted(range(len(bm_ids)), key=lambda i: scores[i], reverse=True)
    bm_rank = {bm_ids[i]: rank for rank, i in enumerate(order, start=1)}

    k = config.RRF_K
    weight = config.BM25_WEIGHT
    unranked = len(bm_ids) + 1

    def fused(item):
        dense_rank, chunk_id, _ = item
        return 1.0 / (k + dense_rank) + weight / (k + bm_rank.get(chunk_id, unranked))

    items = [
        (rank, chunk_id, result)
        for rank, (chunk_id, result) in enumerate(zip(ids, results), start=1)
    ]
    items.sort(key=fused, reverse=True)
    return [result for _, _, result in items]


def index_exists(corpus: str | None = None, variant: str = "default") -> bool:
    """Is there an index here to search, without searching it?

    `serve.py`'s health check asks this. It deliberately does not embed
    anything: loading the embedding model takes 80 MB and a few seconds, and a
    health check that heavy is a health check nobody can afford to call.
    """
    try:
        collection = _client().get_collection(config.collection_name(corpus, variant))
        return collection.count() > 0
    except Exception:
        return False


def reset():
    """Delete every index. Occasionally the fastest way out of a mess."""
    if config.CHROMA_DIR.exists():
        shutil.rmtree(config.CHROMA_DIR)
