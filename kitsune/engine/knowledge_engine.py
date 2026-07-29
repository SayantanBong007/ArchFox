import os
from configs.logger import get_logger
from kitsune.indexer import Indexer
from kitsune.graph.neo4j_store import Neo4jStore
from kitsune.store.chroma_store import ChromaStore
from kitsune.query.hybrid_search import HybridSearcher
from kitsune.query.synthesizer import Synthesizer

logger = get_logger(__name__)

class RepositoryKnowledgeEngine:
    """
    The unified programmatic interface for Kitsune.
    This replaces basic GraphRAG by providing strictly structured topological
    data and semantic context for autonomous agents to use.
    """

    def __init__(self, chroma_path: str = None):
        if not chroma_path:
            # Default to the ArchFox data directory
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            chroma_path = os.path.join(base_dir, "data", "chroma_test")
            
        self.chroma_store = ChromaStore(chroma_path)
        self.graph_store = Neo4jStore()
        self.hybrid_searcher = HybridSearcher(self.chroma_store, self.graph_store)

    def index_repository(self, repo_path: str):
        """Parse, chunk, and index an entire repository into Graph + Vector DBs."""
        indexer = Indexer(self.chroma_store, self.graph_store)
        indexer.index_directory(repo_path)
        logger.info(f"Indexed {repo_path} into Repository Knowledge Engine.")

    def search_semantic(self, query: str, top_k: int = 5) -> str:
        """Standard semantic search + graph context (GraphRAG)."""
        result_dict = self.hybrid_searcher.search(query, k_primary=top_k)
        # Format the raw dictionary into a string of code blocks for the agents
        synthesizer = Synthesizer()
        return synthesizer._format_context(result_dict)

    def get_source_code(self, entity_name: str) -> str | None:
        """Retrieve the exact source code for a specific function/class."""
        # Query ChromaDB exactly for the name
        results = self.chroma_store.get_by_name(entity_name)
        if results and len(results) > 0:
            return results[0].get("text")
        return None

    def get_downstream_dependencies(self, entity_name: str) -> list[str]:
        """Find all functions that this entity calls."""
        return self.graph_store.get_dependencies(entity_name)

    def get_upstream_callers(self, entity_name: str) -> list[str]:
        """Find all functions that call this entity."""
        return self.graph_store.get_upstream_callers(entity_name)

    def get_call_graph(self, entity_name: str, depth: int = 2) -> dict:
        """Return a structured topology of the call graph centered on this entity."""
        graph = {
            "entity": entity_name,
            "metadata": self.graph_store.get_node_metadata(entity_name),
            "calls": self.get_downstream_dependencies(entity_name),
            "called_by": self.get_upstream_callers(entity_name)
        }
        return graph
