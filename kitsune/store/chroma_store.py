"""ChromaDB vector store — stores chunk embeddings and searches them by similarity.

WHAT IS A VECTOR DATABASE?
===========================
A vector database stores lists of numbers (embeddings) and lets you
ask: "which stored vectors are most similar to this new vector?"

That's how semantic search works:
  1. You embed your query → [0.2, -0.8, 0.41, ...]
  2. You search: "find the 5 stored vectors closest to this"
  3. The DB returns the 5 most similar chunks

WHY CHROMADB?
=============
ChromaDB is the simplest vector database to use for learning:
- One Python package, no server to install or run
- Saves everything to a local folder automatically
- Very clean API: add() to store, query() to search
- Used widely in LangChain, LlamaIndex tutorials

ChromaDB CONCEPTS:
==================
- Client:     the connection to the database
- Collection: like a table — holds all your vectors for one project
- Document:   the text you stored (we store the chunk code)
- Embedding:  the vector for that document
- Metadata:   extra info stored alongside (file path, line numbers, etc.)
- ID:         a unique string ID for each stored item

When you query(), ChromaDB returns the nearest neighbours sorted by
distance (smaller distance = more similar).
"""

from __future__ import annotations

import logging
import os
import uuid

import chromadb
from chromadb.config import Settings

from kitsune.models.chunk import Chunk

logger = logging.getLogger(__name__)

COLLECTION_NAME = "kitsune_chunks"


class ChromaStore:
    """Wraps ChromaDB for storing and searching chunk embeddings.

    Usage
    -----
    store = ChromaStore()
    store.upsert_batch(chunks, vectors)
    results = store.search(query_vector, k=5)
    """

    def __init__(self, path: str | None = None):
        """Connect to a local persistent ChromaDB instance.

        Parameters
        ----------
        path:
            Folder where ChromaDB stores its data.
            Defaults to the CHROMA_PATH env variable, or ./data/chroma.
        """
        chroma_path = path or os.getenv("CHROMA_PATH", "./data/chroma")
        os.makedirs(chroma_path, exist_ok=True)

        # PersistentClient saves everything to disk automatically.
        # No need to call .persist() — it's always written through.
        self._client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False),  # no telemetry
        )
        logger.info(f"ChromaDB connected at: {chroma_path}")

        # get_or_create_collection — creates if it doesn't exist, returns it
        # if it does. We set embedding_function=None because we provide our
        # own vectors (from sentence-transformers). ChromaDB has its own
        # built-in embedder but we want to control exactly which model is used.
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
            # hnsw:space = "cosine" tells ChromaDB to use cosine similarity
            # for nearest-neighbour search (same as our normalized embeddings)
        )
        logger.info(f"Collection '{COLLECTION_NAME}' ready "
                    f"({self._collection.count()} items)")

    def upsert_batch(self, chunks: list[Chunk], vectors: list[list[float]]):
        """Store many chunks + their vectors at once.

        ChromaDB's add() takes parallel lists:
          - ids:        unique string IDs (we generate UUIDs)
          - embeddings: the vectors
          - documents:  the text (we store contextualized chunk text)
          - metadatas:  dicts with extra info (file path, line numbers, etc.)

        Parameters
        ----------
        chunks:
            Chunk objects from K1's chunker.
        vectors:
            Embedding vectors from K2's embedder (same order as chunks).
        """
        ids        = [str(uuid.uuid4()) for _ in chunks]
        documents  = [c.text for c in chunks]
        metadatas  = [
            {
                "chunk_type": c.chunk_type,
                "name":       c.name,
                "file_path":  c.file_path,
                "start_line": c.start_line,
                "end_line":   c.end_line,
                "docstring":  c.docstring,
                "language":   c.language,
            }
            for c in chunks
        ]

        self._collection.add(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Stored {len(chunks)} chunks. "
                    f"Total in DB: {self._collection.count()}")

    def search(self, query_vector: list[float], k: int = 5) -> list[dict]:
        """Find the k most similar chunks to the query vector.

        Parameters
        ----------
        query_vector:
            The embedding of the search query.
        k:
            How many results to return.

        Returns
        -------
        List of result dicts — each contains chunk metadata + 'text' + 'score'.
        Score is the cosine similarity (higher = more similar).
        """
        results = self._collection.query(
            query_embeddings=[query_vector],
            n_results=min(k, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        # ChromaDB returns nested lists (one list per query).
        # We only sent one query, so we unpack [0].
        docs      = results["documents"][0]
        metas     = results["metadatas"][0]
        distances = results["distances"][0]

        output = []
        for doc, meta, dist in zip(docs, metas, distances):
            # ChromaDB returns DISTANCE (lower = more similar).
            # Convert to SIMILARITY (higher = more similar) for consistency
            # with the Qdrant version: similarity = 1 - distance
            score = round(1.0 - dist, 4)
            output.append({**meta, "text": doc, "score": score})

        return output

    def get_by_name(self, name: str) -> list[dict]:
        """Fetch chunks by exact function/class name using metadata filtering.

        Parameters
        ----------
        name:
            The name to look for (e.g. "chunk_file")

        Returns
        -------
        List of result dicts containing metadata and text.
        """
        results = self._collection.get(
            where={"name": name},
            include=["documents", "metadatas"]
        )

        output = []
        if not results["documents"]:
            return output
            
        docs = results["documents"]
        metas = results["metadatas"]

        for doc, meta in zip(docs, metas):
            output.append({**meta, "text": doc})

        return output

    def count(self) -> int:
        """Return the total number of stored chunks."""
        return self._collection.count()
