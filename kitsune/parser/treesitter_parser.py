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
import tree_sitter_javascript as tsjavascript
import tree_sitter_typescript as tstypescript
import tree_sitter_c_cpp as tscpp
import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_rust as tsrust
from tree_sitter import Language, Node, Parser

# Build the language objects once at import time.
LANGUAGES = {
    ".py": Language(tspython.language()),
    ".js": Language(tsjavascript.language()),
    ".jsx": Language(tsjavascript.language()),
    ".ts": Language(tstypescript.language_typescript()),
    ".tsx": Language(tstypescript.language_tsx()),
    ".cpp": Language(tscpp.language_cpp()),
    ".cc": Language(tscpp.language_cpp()),
    ".c": Language(tscpp.language_c()),
    ".go": Language(tsgo.language()),
    ".java": Language(tsjava.language()),
    ".rs": Language(tsrust.language()),
}


def make_parser(ext: str) -> Parser:
    """Return a configured tree-sitter Parser for the given extension."""
    lang = LANGUAGES.get(ext)
    if not lang:
        raise ValueError(f"Unsupported language extension: {ext}")
    return Parser(lang)


def parse_file(path: str | Path) -> tuple[Node, bytes]:
    """Parse a source file and return the root AST node + raw bytes."""
    path_obj = Path(path)
    source = path_obj.read_bytes()
    parser = make_parser(path_obj.suffix)
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
