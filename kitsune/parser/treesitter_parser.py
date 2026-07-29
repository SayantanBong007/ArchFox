"""tree-sitter based Python parser.

WHY tree-sitter instead of Python's built-in `ast` module?
------------------------------------------------------------
Python's `ast` module only parses Python. tree-sitter supports 50+
languages with the same API — the same parser code will work for
JavaScript, TypeScript, Go, Rust, Java etc. when we add them in later
phases. We pay a small extra setup cost now so Kitsune is never
limited to Python-only repos.

HOW tree-sitter works (the key idea):
--------------------------------------
tree-sitter parses source code into a **concrete syntax tree** (CST) —
a tree where every node corresponds to a real token or construct in the
source. It gives us:
  - The node TYPE (e.g. "function_definition", "class_definition")
  - The node's TEXT (the actual source code it spans)
  - Start/end BYTE offsets and LINE/COLUMN positions

We walk this tree to find the nodes we care about (functions, classes)
and extract them as Chunks.
"""

from __future__ import annotations

from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

# Build the Python language object once at import time.
# Language() wraps the compiled grammar so the Parser knows how to
# tokenise and structure Python source code.
PYTHON_LANGUAGE = Language(tspython.language())


def make_parser() -> Parser:
    """Return a configured tree-sitter Parser for Python."""
    return Parser(PYTHON_LANGUAGE)


def parse_file(path: str | Path) -> tuple[Node, bytes]:
    """Parse a Python source file and return the root AST node + raw bytes.

    Parameters
    ----------
    path:
        Path to the .py file to parse.

    Returns
    -------
    root_node:
        The root Node of the concrete syntax tree.
    source_bytes:
        The raw UTF-8 bytes of the file (needed to extract text from
        byte-offset ranges that tree-sitter gives us).
    """
    source = Path(path).read_bytes()
    parser = make_parser()
    tree = parser.parse(source)
    return tree.root_node, source


def get_node_text(node: Node, source: bytes) -> str:
    """Extract the source text for a given node using its byte offsets."""
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def get_node_start_line(node: Node) -> int:
    """Return the 1-indexed start line of a node."""
    return node.start_point[0] + 1   # tree-sitter uses 0-indexed rows


def get_node_end_line(node: Node) -> int:
    """Return the 1-indexed end line of a node."""
    return node.end_point[0] + 1
