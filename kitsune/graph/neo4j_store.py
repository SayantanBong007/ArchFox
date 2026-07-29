"""Neo4j Store — stores the dependency graph of the codebase.

WHAT IS A KNOWLEDGE GRAPH?
==========================
Instead of just storing disconnected code chunks in a vector database,
we store the *relationships* between them.

For Kitsune, our graph looks like this:
- Nodes: Chunks (functions, classes)
- Edges: "CALLS" (e.g. `handle_checkout` CALLS `charge_stripe`)

WHY NETWORKX INSTEAD OF NEO4J?
==============================
Neo4j is the industry standard graph database, but running a heavy Java-based Docker container 
in a CI/CD pipeline (like GitHub Actions) often leads to connection timeouts and out-of-memory errors.

We have rewritten this store to use `networkx`, an in-memory graph library. 
It requires zero setup, zero docker containers, and runs instantly in CI/CD!
"""

from __future__ import annotations

import logging
import networkx as nx

from kitsune.models.chunk import Chunk

logger = logging.getLogger(__name__)


class Neo4jStore:
    """Uses NetworkX under the hood to mock a Graph Database in CI/CD."""

    def __init__(self):
        self.graph = nx.DiGraph()
        logger.info("Initialized in-memory NetworkX Graph (Mocking Neo4j)")

    def close(self):
        pass

    def _make_id(self, chunk: Chunk) -> str:
        """Create a unique string ID for a chunk node."""
        return f"{chunk.file_path}::{chunk.name}"

    def upsert_chunk_node(self, chunk: Chunk):
        node_id = self._make_id(chunk)
        self.graph.add_node(
            node_id,
            name=chunk.name,
            type=chunk.chunk_type,
            file_path=chunk.file_path,
            start_line=chunk.start_line,
            end_line=chunk.end_line
        )

    def add_call_edge(self, caller_chunk: Chunk, callee_name: str):
        caller_id = self._make_id(caller_chunk)
        
        # Find if callee_name exists in any node
        callee_id = next((n for n, d in self.graph.nodes(data=True) if d.get('name') == callee_name), None)
        
        if not callee_id:
            # Create stub node just like original Neo4j
            callee_id = f"stub::{callee_name}"
            self.graph.add_node(callee_id, name=callee_name)
            
        self.graph.add_edge(caller_id, callee_id, type="CALLS")

    def get_dependencies(self, chunk_name: str) -> list[str]:
        # Find nodes with name == chunk_name
        nodes = [n for n, d in self.graph.nodes(data=True) if d.get('name') == chunk_name]
        deps = []
        for n in nodes:
            for successor in self.graph.successors(n):
                deps.append(self.graph.nodes[successor].get('name'))
        return deps

    def get_upstream_callers(self, chunk_name: str) -> list[str]:
        nodes = [n for n, d in self.graph.nodes(data=True) if d.get('name') == chunk_name]
        callers = []
        for n in nodes:
            for predecessor in self.graph.predecessors(n):
                callers.append(self.graph.nodes[predecessor].get('name'))
        return callers

    def get_node_metadata(self, chunk_name: str) -> dict | None:
        nodes = [n for n, d in self.graph.nodes(data=True) if d.get('name') == chunk_name]
        if nodes:
            data = self.graph.nodes[nodes[0]]
            return {
                "file": data.get("file_path"),
                "start_line": data.get("start_line"),
                "end_line": data.get("end_line"),
                "type": data.get("type")
            }
        return None

    def clear_all(self):
        self.graph.clear()
