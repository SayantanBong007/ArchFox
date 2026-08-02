"""Neo4j Store — stores the dependency graph of the codebase.

WHAT IS A KNOWLEDGE GRAPH?
==========================
Instead of just storing disconnected code chunks in a vector database,
we store the *relationships* between them.

For Kitsune, our graph looks like this:
- Nodes: Chunks (functions, classes)
- Edges: "CALLS" (e.g. `handle_checkout` CALLS `charge_stripe`)

WHY NEO4J?
==========
Neo4j is the industry standard graph database. It uses a query language
called Cypher. For example, to find everything a function calls:
    MATCH (caller:Chunk {name: 'handle_checkout'})-[r:CALLS]->(callee)
    RETURN callee

When a user asks a complex question, we can find the starting node via
ChromaDB (vector search), and then query Neo4j to find all its dependencies
so the LLM sees the complete execution path!
"""

from __future__ import annotations

import logging
import os
import networkx as nx

from neo4j import GraphDatabase
from kitsune.models.chunk import Chunk

logger = logging.getLogger(__name__)

class Neo4jStore:
    """Wraps Neo4j for storing and querying the code dependency graph.
    
    If Neo4j is unavailable (e.g. in GitHub Actions), this gracefully 
    falls back to an in-memory NetworkX graph!
    """

    def __init__(self):
        """Try to connect to Neo4j, fallback to NetworkX if it fails."""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "kitsune_password")
        
        self._driver = None
        self.use_fallback = False
        self.nx_graph = None
        
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            self._driver.verify_connectivity()
            logger.info(f"Neo4j connected successfully at {uri}!")
            self._setup_constraints()
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
            logger.warning("Falling back to in-memory NetworkX Graph!")
            self._driver = None
            self.use_fallback = True
            self.nx_graph = nx.DiGraph()

    def close(self):
        if self._driver:
            self._driver.close()

    def _setup_constraints(self):
        if self.use_fallback: return
        query = """
        CREATE CONSTRAINT chunk_id IF NOT EXISTS 
        FOR (c:Chunk) REQUIRE c.id IS UNIQUE
        """
        assert self._driver is not None
        with self._driver.session() as session:
            try:
                session.run(query)
            except Exception as e:
                logger.debug(f"Could not create constraint: {e}")

    def _make_id(self, chunk: Chunk) -> str:
        return f"{chunk.file_path}::{chunk.name}"

    def upsert_chunk_node(self, chunk: Chunk):
        if self.use_fallback:
            assert self.nx_graph is not None
            node_id = self._make_id(chunk)
            self.nx_graph.add_node(
                node_id,
                name=chunk.name,
                type=chunk.chunk_type,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line
            )
            return

        query = """
        MERGE (c:Chunk {id: $id})
        SET c.name = $name, c.type = $type, c.file_path = $file_path,
            c.start_line = $start_line, c.end_line = $end_line
        """
        assert self._driver is not None
        with self._driver.session() as session:
            session.run(query, id=self._make_id(chunk), name=chunk.name,
                        type=chunk.chunk_type, file_path=chunk.file_path,
                        start_line=chunk.start_line, end_line=chunk.end_line)

    def add_call_edge(self, caller_chunk: Chunk, callee_name: str):
        if self.use_fallback:
            assert self.nx_graph is not None
            caller_id = self._make_id(caller_chunk)
            callee_id = next((n for n, d in self.nx_graph.nodes(data=True) if d.get('name') == callee_name), None)
            if not callee_id:
                callee_id = f"stub::{callee_name}"
                self.nx_graph.add_node(callee_id, name=callee_name)
            self.nx_graph.add_edge(caller_id, callee_id, type="CALLS")
            return

        query = """
        MATCH (caller:Chunk {id: $caller_id})
        MERGE (callee:Chunk {name: $callee_name})
        MERGE (caller)-[:CALLS]->(callee)
        """
        assert self._driver is not None
        with self._driver.session() as session:
            session.run(query, caller_id=self._make_id(caller_chunk), callee_name=callee_name)

    def get_dependencies(self, chunk_name: str) -> list[str]:
        if self.use_fallback:
            assert self.nx_graph is not None
            nodes = [n for n, d in self.nx_graph.nodes(data=True) if d.get('name') == chunk_name]
            deps = []
            for n in nodes:
                for successor in self.nx_graph.successors(n):
                    deps.append(self.nx_graph.nodes[successor].get('name'))
            return deps

        if not self._driver: return []
        query = "MATCH (caller:Chunk {name: $name})-[:CALLS]->(callee) RETURN callee.name AS callee_name"
        assert self._driver is not None
        with self._driver.session() as session:
            result = session.run(query, name=chunk_name)
            return [record["callee_name"] for record in result]
            
    def get_upstream_callers(self, chunk_name: str) -> list[str]:
        if self.use_fallback:
            assert self.nx_graph is not None
            nodes = [n for n, d in self.nx_graph.nodes(data=True) if d.get('name') == chunk_name]
            callers = []
            for n in nodes:
                for predecessor in self.nx_graph.predecessors(n):
                    callers.append(self.nx_graph.nodes[predecessor].get('name'))
            return callers

        if not self._driver: return []
        query = "MATCH (caller:Chunk)-[:CALLS]->(callee:Chunk {name: $name}) RETURN caller.name AS caller_name"
        assert self._driver is not None
        with self._driver.session() as session:
            result = session.run(query, name=chunk_name)
            return [record["caller_name"] for record in result]

    def get_node_metadata(self, chunk_name: str) -> dict | None:
        if self.use_fallback:
            assert self.nx_graph is not None
            nodes = [n for n, d in self.nx_graph.nodes(data=True) if d.get('name') == chunk_name]
            if nodes:
                data = self.nx_graph.nodes[nodes[0]]
                return {"file": data.get("file_path"), "start_line": data.get("start_line"), 
                        "end_line": data.get("end_line"), "type": data.get("type")}
            return None

        if not self._driver: return None
        query = """MATCH (c:Chunk {name: $name}) RETURN c.file_path AS file, c.start_line AS start_line, 
                   c.end_line AS end_line, c.type AS type LIMIT 1"""
        assert self._driver is not None
        with self._driver.session() as session:
            result = session.run(query, name=chunk_name).single()
            if result: return dict(result)
            return None

    def clear_all(self):
        if self.use_fallback:
            assert self.nx_graph is not None
            self.nx_graph.clear()
            return
            
        if not self._driver: return
        query = "MATCH (n) DETACH DELETE n"
        assert self._driver is not None
        with self._driver.session() as session:
            session.run(query)
