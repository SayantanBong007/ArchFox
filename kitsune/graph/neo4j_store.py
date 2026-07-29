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

from neo4j import GraphDatabase

from kitsune.models.chunk import Chunk

logger = logging.getLogger(__name__)


class Neo4jStore:
    """Wraps Neo4j for storing and querying the code dependency graph."""

    def __init__(self):
        """Connect to the Neo4j database."""
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "kitsune_password")
        
        try:
            self._driver = GraphDatabase.driver(uri, auth=(user, password))
            # Verify connection
            self._driver.verify_connectivity()
            logger.info(f"Neo4j connected at {uri}")
            self._setup_constraints()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j. Is the Docker container running? Error: {e}")
            self._driver = None

    def close(self):
        if self._driver:
            self._driver.close()

    def _setup_constraints(self):
        """Create a uniqueness constraint on chunk IDs to prevent duplicates."""
        if not self._driver:
            return
            
        # We'll use a combination of file_path and name as a unique ID for nodes
        query = """
        CREATE CONSTRAINT chunk_id IF NOT EXISTS 
        FOR (c:Chunk) REQUIRE c.id IS UNIQUE
        """
        with self._driver.session() as session:
            try:
                session.run(query)
            except Exception as e:
                logger.debug(f"Could not create constraint (might already exist): {e}")

    def _make_id(self, chunk: Chunk) -> str:
        """Create a unique string ID for a chunk node."""
        return f"{chunk.file_path}::{chunk.name}"

    def upsert_chunk_node(self, chunk: Chunk):
        """Store a chunk as a node in the graph.
        
        MERGE acts like an 'upsert' in Cypher. If the node exists, it updates it.
        If it doesn't, it creates it.
        """
        if not self._driver:
            return

        query = """
        MERGE (c:Chunk {id: $id})
        SET c.name = $name,
            c.type = $type,
            c.file_path = $file_path,
            c.start_line = $start_line,
            c.end_line = $end_line
        """
        with self._driver.session() as session:
            session.run(query, 
                        id=self._make_id(chunk),
                        name=chunk.name,
                        type=chunk.chunk_type,
                        file_path=chunk.file_path,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line)

    def add_call_edge(self, caller_chunk: Chunk, callee_name: str):
        """Create a CALLS edge from a chunk to another function name.
        
        Notice how we MERGE the callee based only on its name.
        If we haven't indexed the callee's file yet, this creates a "stub" node
        that just has the name. When we do index the callee's file later,
        upsert_chunk_node will fill in the rest of its properties!
        """
        if not self._driver:
            return

        # We assume the callee name is unique enough for this simple demo.
        # In a real system, you'd try to resolve the exact file path of the callee.
        query = """
        MATCH (caller:Chunk {id: $caller_id})
        MERGE (callee:Chunk {name: $callee_name})
        MERGE (caller)-[:CALLS]->(callee)
        """
        with self._driver.session() as session:
            session.run(query, 
                        caller_id=self._make_id(caller_chunk),
                        callee_name=callee_name)

    def get_dependencies(self, chunk_name: str) -> list[str]:
        """Find everything a specific chunk calls.
        
        This is the magic of GraphRAG! We just follow the arrows.
        """
        if not self._driver:
            return []

        query = """
        MATCH (caller:Chunk {name: $name})-[:CALLS]->(callee)
        RETURN callee.name AS callee_name
        """
        with self._driver.session() as session:
            result = session.run(query, name=chunk_name)
            return [record["callee_name"] for record in result]
            
    def get_upstream_callers(self, chunk_name: str) -> list[str]:
        """Find all functions that call a specific chunk.
        
        This finds the 'upstream' dependencies. If I change 'chunk_name',
        these are the functions that might break!
        """
        if not self._driver:
            return []

        query = """
        MATCH (caller:Chunk)-[:CALLS]->(callee:Chunk {name: $name})
        RETURN caller.name AS caller_name
        """
        with self._driver.session() as session:
            result = session.run(query, name=chunk_name)
            return [record["caller_name"] for record in result]

    def get_node_metadata(self, chunk_name: str) -> dict | None:
        """Fetch the structural metadata (file, lines, type) for a node."""
        if not self._driver:
            return None
            
        query = """
        MATCH (c:Chunk {name: $name})
        RETURN c.file_path AS file, c.start_line AS start_line, 
               c.end_line AS end_line, c.type AS type
        LIMIT 1
        """
        with self._driver.session() as session:
            result = session.run(query, name=chunk_name).single()
            if result:
                return dict(result)
            return None

            
    def clear_all(self):
        """Delete all nodes and edges (useful for tests)."""
        if not self._driver:
            return
        query = "MATCH (n) DETACH DELETE n"
        with self._driver.session() as session:
            session.run(query)
