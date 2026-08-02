"""AST-aware chunker.

WHY chunk at AST boundaries instead of fixed line counts?
----------------------------------------------------------
Most RAG systems split files every N lines (e.g. every 50 lines).
This is fast but dumb — it routinely cuts a function in half, leaving
chunks with no beginning or no end, which means:
  - The embedding captures incomplete meaning
  - An LLM retrieving the chunk can't tell what the function does
  - Context about *what class a method belongs to* is lost

Chunking at AST boundaries (function/class definitions) means every
chunk is a complete, meaningful unit. A function chunk always has its
full signature, body, and docstring. A class chunk always includes
its full definition. This makes embeddings dramatically more accurate.

WHAT this module produces:
---------------------------
Given a source file, it returns a list of Chunk objects — one per
top-level function or class, plus one for any module-level code that
sits between them (imports, constants, module docstrings).
"""

from __future__ import annotations

from pathlib import Path

from tree_sitter import Node

from kitsune.models.chunk import Chunk
from kitsune.parser.treesitter_parser import (
    get_node_end_line,
    get_node_start_line,
    get_node_text,
    parse_file,
)

# The tree-sitter node types we treat as chunk boundaries.
# Everything inside these nodes becomes its own chunk.
_CHUNK_NODE_TYPES = {
    "function_definition", "class_definition",     # Python
    "function_declaration", "class_declaration",   # JS/TS/C++
    "arrow_function", "method_definition",         # JS/TS
    "method_declaration",                          # Java
    "function_item", "impl_item",                  # Rust
    "struct_type", "interface_type",               # Go
    "struct_specifier", "class_specifier",         # C++
}


def _extract_name(node: Node, source: bytes) -> str:
    """Extract the identifier name from a function or class node.

    tree-sitter represents a function like:
        function_definition
          name: identifier     ← this is the child we want
          parameters: ...
          body: ...

    We find the "name" child and return its text.
    """
    for child in node.children:
        if child.type == "identifier":
            return get_node_text(child, source)
    return ""


def _extract_docstring(node: Node, source: bytes) -> str:
    """Extract the docstring from a function or class node, if present.

    A docstring in the AST appears as the first statement in the body,
    and that statement is an expression_statement containing a string.

    tree-sitter structure:
        block
          expression_statement
            string    ← the docstring
    """
    for child in node.children:
        if child.type == "block":
            for stmt in child.children:
                if stmt.type == "expression_statement":
                    for inner in stmt.children:
                        if inner.type == "string":
                            raw = get_node_text(inner, source)
                            # Strip surrounding quotes
                            return raw.strip("\"'").strip()
    return ""


def _node_type_to_chunk_type(node_type: str) -> str:
    if node_type in {"function_definition", "function_declaration", "arrow_function", "method_definition", "method_declaration", "function_item"}:
        return "function"
    return "class"


def chunk_file(file_path: str | Path) -> list[Chunk]:
    """Parse a Python file and return a list of AST-aware Chunks.

    Strategy
    --------
    1. Parse the file with tree-sitter → get the root node.
    2. Walk the *top-level* children of the module node.
    3. For each top-level function or class → produce a Chunk.
    4. For any runs of non-function/non-class nodes (imports, module-level
       constants, standalone expressions) → collect them into a single
       "module" Chunk so nothing is silently discarded.

    Nested functions and methods inside classes are NOT recursively
    expanded in K1 — the whole class body is one chunk. We add nested
    chunking in a later phase once the basic pipeline is working.

    Parameters
    ----------
    file_path:
        Path to a Python source file.

    Returns
    -------
    List of Chunk objects, ordered by their position in the file.
    """
    path = Path(file_path)
    root_node, source = parse_file(path)

    chunks: list[Chunk] = []
    module_level_nodes: list[Node] = []  # accumulate non-function/class nodes

    def flush_module_nodes():
        """Turn any accumulated module-level nodes into a single Chunk."""
        if not module_level_nodes:
            return
        # Filter out pure whitespace / newline nodes
        meaningful = [n for n in module_level_nodes if n.text and n.text.strip()]
        if not meaningful:
            module_level_nodes.clear()
            return

        combined_text = "\n".join(
            get_node_text(n, source) for n in meaningful
        )
        chunks.append(Chunk(
            text=combined_text,
            chunk_type="module",
            name="<module>",
            file_path=str(path),
            start_line=get_node_start_line(meaningful[0]),
            end_line=get_node_end_line(meaningful[-1]),
        ))
        module_level_nodes.clear()

    # Walk direct children of the module root
    for child in root_node.children:
        if child.type in _CHUNK_NODE_TYPES:
            flush_module_nodes()   # close off any preceding module-level block

            chunk_type = _node_type_to_chunk_type(child.type)
            name = _extract_name(child, source)
            docstring = _extract_docstring(child, source)
            text = get_node_text(child, source)

            chunks.append(Chunk(
                text=text,
                chunk_type=chunk_type,
                name=name,
                file_path=str(path),
                start_line=get_node_start_line(child),
                end_line=get_node_end_line(child),
                docstring=docstring,
            ))
        else:
            module_level_nodes.append(child)

    flush_module_nodes()   # handle any trailing module-level code
    return chunks
