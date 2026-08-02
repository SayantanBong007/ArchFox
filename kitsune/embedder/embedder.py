"""Embedder — converts text into vectors using sentence-transformers.

WHAT IS AN EMBEDDING?
=====================
An embedding is a list of numbers (a "vector") that represents the
MEANING of a piece of text. Similar texts produce similar vectors.

Example:
  "process a payment"    → [0.23, -0.87, 0.41, ...]  (384 numbers)
  "charge a credit card" → [0.21, -0.85, 0.39, ...]  (very similar!)
  "bake a chocolate cake"→ [0.91,  0.34, -0.72, ...] (very different)

The model we use is BAAI/bge-small-en-v1.5:
- Small (120MB) — runs fast on CPU, no GPU needed
- 384 dimensions — each text becomes a list of 384 floats
- Trained specifically for retrieval tasks
- Same model ArchFox v3 used, so we already know it works

WHY NOT USE AN OPENAI EMBEDDING API?
=====================================
We could call OpenAI's text-embedding-3-small, but:
1. It costs money per token
2. Your code leaves your machine (privacy issue for codebases)
3. It requires internet (offline repos break)

A local sentence-transformers model is free, private, and offline.
"""

from __future__ import annotations

import logging
from typing import Union

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# The model name — this is downloaded once and cached by sentence-transformers.
# Find it at https://huggingface.co/BAAI/bge-small-en-v1.5
MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Module-level singleton so we only load the model once per process.
# Loading a model takes ~1 second — we don't want to do it per chunk.
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Load the model on first call; return cached instance afterwards."""
    global _model
    if _model is None:
        logger.info(f"Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
        logger.info("Embedding model loaded.")
    return _model


def embed(text: str) -> list[float]:
    """Embed a single string into a vector.

    Parameters
    ----------
    text:
        The text to embed. For Kitsune this is always the contextualized
        chunk text (context note + original code).

    Returns
    -------
    A list of 384 floats — the embedding vector.
    """
    model = _get_model()
    vector = model.encode(text, normalize_embeddings=True)
    # normalize_embeddings=True scales the vector to unit length.
    # This makes cosine similarity equivalent to dot product — faster search.
    return vector.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings at once — much faster than embedding one by one.

    sentence-transformers can process a batch in parallel on the same
    forward pass. For a repo with 500 chunks, batching is 10-20x faster
    than calling embed() 500 times.

    Parameters
    ----------
    texts:
        List of strings to embed.

    Returns
    -------
    List of embedding vectors, one per input text (same order).
    """
    model = _get_model()
    vectors = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    return [v.tolist() for v in vectors]


def embedding_dim() -> int:
    """Return the number of dimensions in each embedding vector (384)."""
    return _get_model().get_sentence_embedding_dimension() or 384
