# 001. Use Qdrant as the vector store

## Status
Accepted

## Context
The retrieval module needs a vector database to store code-chunk embeddings and run similarity search for the reviewer agent's context retrieval.

Two options were considered:
- **Qdrant** — dedicated vector database, run as a local/Docker server or via Qdrant Cloud.
- **Chroma** — embedded, in-process vector store with no separate server required.

Chroma is simpler to start with (no server to run), but Qdrant scales better beyond local prototyping and is easier to run as a shared service if ArchFox is later used by more than one developer or deployed centrally.

## Decision
Use Qdrant (`retrieval/vectorstore/qdrant_client.py`) as the vector store, accessed through a small wrapper (`QdrantVectorStore`) exposing `upsert` and `search`.

## Consequences
- Requires a running Qdrant instance (local Docker container or Qdrant Cloud) before the retrieval module is functional.
- The wrapper interface (`upsert`/`search`) is intentionally minimal, so swapping in Chroma later only requires a new implementation behind the same interface, not changes to callers.
