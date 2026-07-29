"""Hybrid Search — The bridge between Semantic (ChromaDB) and Structural (Neo4j) search.

HOW THIS WORKS:
1. Embed the user's question.
2. Ask ChromaDB: "Give me the 3 chunks that match this meaning."
3. For each of those 3 chunks, ask Neo4j: "What do these chunks call?"
4. For every dependency Neo4j finds, go back to ChromaDB and fetch its actual code.
5. Combine it all into one massive string of context for the LLM.
"""

import logging
from sentence_transformers import SentenceTransformer
from typing import TypedDict

from kitsune.store.chroma_store import ChromaStore
from kitsune.graph.neo4j_store import Neo4jStore

logger = logging.getLogger(__name__)


class SearchResult(TypedDict):
    primary_chunks: list[dict]
    dependency_chunks: list[dict]


class HybridSearcher:
    """Combines Vector and Graph search."""

    def __init__(self, chroma_store: ChromaStore | None = None, graph_store: Neo4jStore | None = None, chroma_path: str | None = None):
        self._store = chroma_store or ChromaStore(path=chroma_path)
        self._graph = graph_store or Neo4jStore()

        
        # Load the same small model we used in K2 for embeddings
        logger.info("Loading embedding model for queries...")
        self._embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
        
    def search(self, query: str, k_primary: int = 3) -> SearchResult:
        """Run the hybrid GraphRAG search pipeline."""
        
        # Step 1: Embed the question
        query_vector = self._embedder.encode(query, normalize_embeddings=True).tolist()
        
        # Step 2: Find the primary chunks (Semantic Entry Points)
        primary_chunks = self._store.search(query_vector, k=k_primary)
        
        if not primary_chunks:
            return {"primary_chunks": [], "dependency_chunks": []}
            
        # Step 3: Traverse the Graph for dependencies
        dependency_names = set()
        for chunk in primary_chunks:
            chunk_name = chunk.get("name")
            if chunk_name:
                # Ask Neo4j what this function calls
                calls = self._graph.get_dependencies(chunk_name)
                dependency_names.update(calls)
                
        # Step 4: Fetch the code for all dependencies
        dependency_chunks = []
        for dep_name in dependency_names:
            # We skip pulling the code if it's already in our primary list
            if any(c.get("name") == dep_name for c in primary_chunks):
                continue
                
            dep_results = self._store.get_by_name(dep_name)
            if dep_results:
                dependency_chunks.extend(dep_results)
                
        return {
            "primary_chunks": primary_chunks,
            "dependency_chunks": dependency_chunks
        }
