"""ArchFox's single entry point to Kitsune.

Kitsune is installed as a package (`kitsune-code`, pinned in requirements.txt), not
copied into this repository. Every ArchFox module gets its engine from here so that:

- each reviewed repository has its own index (Kitsune namespace "<owner>__<repo>"),
  instead of every repo landing in one shared index;
- the stores live in ArchFox's data/ folder, not inside site-packages;
- the LangGraph agent tools, the fix agent and the review nodes all share the same
  engine for the repository currently under review.

With no QDRANT_URL / NEO4J_URI set, Kitsune runs on local ChromaDB + NetworkX, so the
GitHub Action needs no database servers.
"""
from __future__ import annotations

import os
import threading

from kitsune.engine.knowledge_engine import RepositoryKnowledgeEngine

ARCHFOX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.getenv("ARCHFOX_KITSUNE_DATA", os.path.join(ARCHFOX_ROOT, "data", "kitsune"))

# Retrieved context per search. Kitsune's own default (10,000 chars) is sized for one
# question; ArchFox runs one search per changed file and then caps the total at 5,000
# chars to stay under Groq's free-tier tokens-per-minute limit, so keep each search
# within that total. An explicit KITSUNE_CONTEXT_BUDGET still wins.
os.environ.setdefault("KITSUNE_CONTEXT_BUDGET", "5000")

_engines: dict[str, RepositoryKnowledgeEngine] = {}
_lock = threading.Lock()
_active: str | None = None


def namespace_for(owner: str, repo: str) -> str:
    """Kitsune namespace for a GitHub repository."""
    return f"{owner}__{repo}"


def get_engine(namespace: str = "") -> RepositoryKnowledgeEngine:
    """Return the (cached) engine for a namespace, creating it on first use."""
    with _lock:
        engine = _engines.get(namespace)
        if engine is None:
            engine = RepositoryKnowledgeEngine(data_dir=DATA_DIR, namespace=namespace or None)
            _engines[namespace] = engine
        return engine


def set_active(namespace: str) -> RepositoryKnowledgeEngine:
    """Mark the repository under review; the agent tools query this engine."""
    global _active
    engine = get_engine(namespace)
    _active = namespace
    return engine


def active_engine() -> RepositoryKnowledgeEngine:
    """Engine for the repository under review (the default index if none is set)."""
    return get_engine(_active or "")
