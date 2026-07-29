"""Chunk — the atomic unit Kitsune works with.

Every piece of code that Kitsune indexes, retrieves, or reasons about
is represented as a Chunk. Think of it as a single, self-contained
piece of knowledge extracted from a source file.
"""

from dataclasses import dataclass, field


@dataclass
class Chunk:
    """A single extracted code unit with full context metadata.

    Attributes
    ----------
    text:
        The raw source code of this chunk — the function body, class
        body, or module-level block as it appears in the file.
    chunk_type:
        One of "function", "class", or "module". Tells downstream
        agents what kind of construct this chunk came from.
    name:
        The identifier name (e.g. "process_payment", "PaymentService").
        Empty string for anonymous module-level blocks.
    file_path:
        Absolute or relative path to the source file this chunk came from.
    start_line:
        1-indexed line number where this chunk starts in the source file.
    end_line:
        1-indexed line number where this chunk ends (inclusive).
    scope:
        The dotted path of parent scopes, e.g. "PaymentService.process"
        for a method. Empty string for top-level constructs.
    docstring:
        The docstring of this function or class, if present. Extracted
        separately so concept extraction can read it without parsing
        the full chunk text.
    language:
        Source language (e.g. "python"). Kitsune will support multiple
        languages in later phases — this field is already here so chunks
        from different languages can be stored and distinguished together.
    """

    text: str
    chunk_type: str          # "function" | "class" | "module"
    name: str
    file_path: str
    start_line: int
    end_line: int
    scope: str = ""
    docstring: str = ""
    language: str = "python"

    def __repr__(self) -> str:
        loc = f"{self.file_path}:{self.start_line}-{self.end_line}"
        return f"Chunk({self.chunk_type} '{self.name}' @ {loc})"
