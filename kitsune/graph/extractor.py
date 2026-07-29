"""Graph Extractor — finds dependencies (calls) inside chunks using the AST.

WHY BUILD A GRAPH? (GraphRAG vs Standard RAG)
=============================================
Standard RAG (Phase K2) only finds chunks that have similar TEXT to your query.

Imagine this code:
    def handle_checkout(cart):
        validate_cart(cart)
        charge_stripe(cart.total)
        send_receipt(cart.user_email)

If you ask: "What happens during checkout?"
Standard RAG finds `handle_checkout`. But it DOES NOT know what `charge_stripe` does!
The AI only sees the name "charge_stripe" but doesn't have the code for it.

GraphRAG fixes this:
1. We parse the code to find every function call.
2. We store these as edges: (handle_checkout) --calls--> (charge_stripe).
3. When you query "checkout", we retrieve `handle_checkout` AND we traverse the
   graph to automatically pull in `charge_stripe` and `send_receipt`.

The AI gets the FULL picture of the execution flow.

HOW IT WORKS:
=============
tree-sitter represents a function call as a "call" node:
    call
      function: identifier → "charge_stripe"
      arguments: argument_list

We walk the AST of a chunk, find every "call" node, extract the function name,
and return it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from tree_sitter import Node

from kitsune.parser.treesitter_parser import get_node_text, parse_file

logger = logging.getLogger(__name__)


def extract_calls(node: Node, source: bytes) -> set[str]:
    """Find all function/method calls inside an AST node.

    We recursively walk the tree. Whenever we hit a 'call' node,
    we look for its 'function' child to get the name of what's being called.

    Parameters
    ----------
    node:
        The tree-sitter Node to search inside (e.g. a function_definition node).
    source:
        The raw bytes of the file, needed to extract the text.

    Returns
    -------
    A set of function names called within this node.
    (Using a set because a function might call the same thing 5 times,
     but we only need one edge in our graph).
    """
    calls = set()

    def walk(n: Node):
        if n.type == "call":
            # In tree-sitter Python, a call node looks like:
            # call
            #   function: identifier (e.g. "print") OR attribute (e.g. "self.db.query")
            #   arguments: argument_list
            for child in n.children:
                # We want the node that represents WHAT is being called.
                # In python grammar, this is named 'function'.
                # Unfortunately, tree-sitter python node types for the callee
                # are just 'identifier' or 'attribute', but the FIELD name is 'function'.
                # However, python tree-sitter library in this version doesn't always
                # expose field names easily in the basic API.
                # A robust heuristic: the callee is the first child of the call node
                # before the argument_list.
                if child.type in ("identifier", "attribute"):
                    callee_text = get_node_text(child, source)
                    # If it's an attribute like 'self.db.query', we extract 'query'
                    # as the base name to match against other chunks.
                    if "." in callee_text:
                        base_name = callee_text.split(".")[-1]
                    else:
                        base_name = callee_text
                    
                    if base_name:
                        calls.add(base_name)
                    break
        
        # Recursively walk children
        for child in n.children:
            walk(child)

    walk(node)
    return calls


def get_chunk_calls(file_path: str, start_line: int, end_line: int) -> set[str]:
    """Extract all function calls from a specific chunk's byte range.
    
    Since we don't save the raw AST node in the Chunk dataclass (it can't be pickled
    easily), we re-parse the file and find the calls within the chunk's line range.
    """
    # This is a bit inefficient (re-parsing the file for each chunk),
    # but fine for K3. In a real production system, we'd extract the calls
    # during K1 while we still have the AST node in memory, and save them
    # directly onto the Chunk object.
    
    path = Path(file_path)
    if not path.exists():
        return set()
        
    root_node, source = parse_file(path)
    
    calls = set()
    
    def walk(n: Node):
        n_start = n.start_point[0] + 1
        n_end = n.end_point[0] + 1
        
        # If this node is completely outside our chunk, skip it
        if n_end < start_line or n_start > end_line:
            return
            
        # If this is a call node within our chunk, extract it
        if n.type == "call" and n_start >= start_line and n_end <= end_line:
            for child in n.children:
                if child.type in ("identifier", "attribute"):
                    callee_text = get_node_text(child, source)
                    base_name = callee_text.split(".")[-1] if "." in callee_text else callee_text
                    if base_name:
                        calls.add(base_name)
                    break
                    
        for child in n.children:
            walk(child)
            
    walk(root_node)
    return calls
