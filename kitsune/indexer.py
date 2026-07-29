"""Indexer — orchestrates the full K1+K2 pipeline.

This is the piece that ties everything together:

    Python file
       │
       ▼  (K1 — chunker)
    List of Chunks
       │
       ▼  (K2 — contextualizer)
    Contextualized texts
    "CONTEXT: This function 'get_user'..."
       │
       ▼  (K2 — embedder)
    Vectors  [0.23, -0.87, 0.41, ...]
       │
       ▼  (K2 — qdrant store)
    Stored in Qdrant DB

After indexing, you can SEARCH:

    Query: "how does authentication work?"
       │
       ▼  (embed the query)
    Query vector
       │
       ▼  (search Qdrant)
    5 most similar chunks
"""

from __future__ import annotations

import logging
from pathlib import Path

from kitsune.embedder.contextualizer import contextualize_chunk
from kitsune.embedder.embedder import embed_batch, embedding_dim
from kitsune.parser.chunker import chunk_file
from kitsune.store.chroma_store import ChromaStore
from kitsune.graph.neo4j_store import Neo4jStore
from kitsune.graph.extractor import get_chunk_calls

logger = logging.getLogger(__name__)


class Indexer:
    """Index Python files into Qdrant for semantic search.

    Usage
    -----
    indexer = Indexer()
    indexer.index_file("path/to/file.py")
    results = indexer.search("how does authentication work?")
    """

    def __init__(self, chroma_store: ChromaStore | None = None, graph_store: Neo4jStore | None = None, chroma_path: str | None = None):
        self._store = chroma_store or ChromaStore(path=chroma_path)
        self._graph = graph_store or Neo4jStore()

    def index_file(self, file_path: str | Path) -> int:
        """Parse, contextualize, embed, and store all chunks from a file.

        Parameters
        ----------
        file_path:
            Path to a Python source file.

        Returns
        -------
        Number of chunks indexed.
        """
        path = Path(file_path)
        logger.info(f"Indexing: {path.name}")

        # ── Step 1: Parse the file into chunks (K1) ──────────────────────────
        chunks = chunk_file(path)
        if not chunks:
            logger.warning(f"No chunks found in {path}")
            return 0
        logger.info(f"  {len(chunks)} chunks from K1 parser")

        # ── Step 2: Contextualize each chunk (K2) ────────────────────────────
        # For each chunk, prepend the context note before embedding.
        # This is what makes the embeddings context-aware.
        contextualized_texts = [contextualize_chunk(c) for c in chunks]
        logger.info(f"  Contextualized {len(chunks)} chunks")

        # ── Step 3: Embed all contextualized texts in one batch ───────────────
        # Batching is much faster than embedding one-by-one.
        vectors = embed_batch(contextualized_texts)
        logger.info(f"  Embedded {len(vectors)} vectors (dim={len(vectors[0])})")

        # ── Step 4: Store chunks + vectors in Qdrant ──────────────────────────
        self._store.upsert_batch(chunks, vectors)
        logger.info(f"  Stored in Chroma. Total in DB: {self._store.count()}")

        # ── Step 5: Build Dependency Graph in Neo4j (K3) ──────────────────────
        graph_edges = 0
        for chunk in chunks:
            if chunk.name == "<module>":
                continue
                
            self._graph.upsert_chunk_node(chunk)
            
            # Extract function calls from this chunk
            calls = get_chunk_calls(chunk.file_path, chunk.start_line, chunk.end_line)
            for callee in calls:
                self._graph.add_call_edge(chunk, callee)
                graph_edges += 1
                
        logger.info(f"  Added {graph_edges} edges to Neo4j Graph")

        return len(chunks)

    def index_directory(self, dir_path: str | Path,
                        extensions: tuple[str, ...] = (".py",)) -> int:
        """Index all files with the given extensions in a directory.

        Parameters
        ----------
        dir_path:
            Root directory to walk.
        extensions:
            File extensions to index (default: Python files only).

        Returns
        -------
        Total number of chunks indexed.
        """
        total = 0
        for path in Path(dir_path).rglob("*"):
            if path.suffix in extensions and path.is_file():
                # Skip hidden dirs, venvs, cache folders
                if any(p.startswith((".", "__")) for p in path.parts):
                    continue
                total += self.index_file(path)
        return total

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Search for chunks semantically similar to the query.

        Parameters
        ----------
        query:
            Natural language question or description.
        k:
            Number of results to return.

        Returns
        -------
        List of result dicts, each containing chunk metadata + 'score'.
        """
        from kitsune.embedder.embedder import embed
        query_vector = embed(query)
        return self._store.search(query_vector, k=k)
