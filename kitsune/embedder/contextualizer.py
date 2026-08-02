"""Contextualizer — prepends a context note to each chunk before embedding.

WHY DOES THIS MATTER?
=====================
When you embed a bare code chunk like:

    def get_user(self, user_id):
        return self.db.query(...)

...the embedding has no idea:
- This is inside a class called UserService
- UserService handles authentication
- The file is services/user_service.py

So if someone searches "how does authentication work?", this function
might never come up — the word "authentication" isn't in it.

THE FIX (Anthropic's Contextual Retrieval):
============================================
Before embedding, prepend a context note:

    CONTEXT: This function 'get_user' belongs to the class 'UserService'
    in kitsune/parser/chunker.py (lines 15-20). It is part of the user
    authentication and profile management system.

    def get_user(self, user_id):
        return self.db.query(...)

Now the embedding captures BOTH what the code does AND where it lives.
The search "how does authentication work?" will find this chunk.

TWO MODES:
==========
1. LLM mode   — uses an LLM (Groq) to write a smart, descriptive note
2. Template mode — uses only the chunk metadata (no API call, no cost)

Template mode is the fallback. It's already useful — it tells the
embedding model the file path, class name, chunk type, and docstring.
LLM mode makes it richer by reading the actual code and summarising it.
"""

from __future__ import annotations

import logging
import os

from kitsune.models.chunk import Chunk

logger = logging.getLogger(__name__)


# ── Template (deterministic) contextualizer ───────────────────────────────────

def build_context_note(chunk: Chunk) -> str:
    """Build a context note from chunk metadata — no LLM needed.

    This is the fallback. Even without an LLM it's far better than
    bare embedding because we attach:
    - the file path (where does this live in the project?)
    - the chunk type and name (is it a function? a class?)
    - the docstring (what does it do, in the author's own words?)

    Parameters
    ----------
    chunk:
        The Chunk object produced by K1's chunker.

    Returns
    -------
    A short context string to prepend before the chunk text.
    """
    parts = [f"CONTEXT: This is a {chunk.chunk_type}"]

    if chunk.name and chunk.name != "<module>":
        parts.append(f"named '{chunk.name}'")

    parts.append(f"in {chunk.file_path}")
    parts.append(f"(lines {chunk.start_line}-{chunk.end_line}).")

    if chunk.docstring:
        # The docstring is the author's own description — use it directly
        doc = chunk.docstring[:200].replace("\n", " ")
        parts.append(f"Description: {doc}")

    return " ".join(parts)


def contextualize_chunk(chunk: Chunk) -> str:
    """Return the full contextualized text for embedding.

    Format:
        [context note]

        [original chunk code]

    This is the string that gets embedded — not the raw chunk text.
    """
    note = build_context_note(chunk)
    return f"{note}\n\n{chunk.text}"


# ── LLM contextualizer (optional, richer) ────────────────────────────────────

async def build_llm_context_note(chunk: Chunk, repo_summary: str = "") -> str:
    """Use an LLM to write a richer context note for the chunk.

    This is the LLM-powered version. It reads the actual code and
    produces a description like:
        "This function validates a payment amount and triggers a charge
         via the Stripe API. It belongs to the billing module."

    Falls back to the template version if no API key is configured
    or if the LLM call fails — so the pipeline always completes.

    Parameters
    ----------
    chunk:
        The chunk to contextualise.
    repo_summary:
        Optional short description of the overall repository, injected
        into the prompt so the LLM can relate the chunk to the bigger picture.
    """
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        logger.debug("No GROQ_API_KEY set — using template contextualizer")
        return build_context_note(chunk)

    try:
        import openai

        client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
        )

        repo_ctx = f"Repository summary: {repo_summary}\n\n" if repo_summary else ""
        prompt = (
            f"{repo_ctx}"
            f"Here is a {chunk.chunk_type} from {chunk.file_path}:\n\n"
            f"```python\n{chunk.text[:1500]}\n```\n\n"
            "Write ONE sentence (max 40 words) explaining what this code does "
            "and what larger feature or system it belongs to. "
            "Start with 'CONTEXT:'. Be specific. Do not repeat the code."
        )

        response = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.0,
        )
        note = (response.choices[0].message.content or "").strip()
        logger.debug(f"LLM context note for '{chunk.name}': {note[:80]}")
        return note

    except Exception as exc:
        logger.warning(f"LLM contextualizer failed for '{chunk.name}': {exc} — using template")
        return build_context_note(chunk)
