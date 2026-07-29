# 002. Use a local sentence-transformers model for embeddings

## Status
Accepted

## Context
Code chunks need to be embedded before being stored in the vector store. Groq (used for the reviewer's chat completions) does not offer an embeddings endpoint, so a separate embedding provider is required.

Options considered:
- Call a hosted embeddings API (e.g. OpenAI embeddings) — adds another paid dependency and API key to manage.
- Run a local embedding model via `sentence-transformers` — free, no API key, works offline, adds a local model download/inference cost instead.

## Decision
Use `sentence-transformers` with the `BAAI/bge-small-en-v1.5` model, run locally in `retrieval/embeddings/embedder.py`. No external embeddings API or key is required.

## Consequences
- No additional API key or per-call cost for embeddings.
- First run downloads the model weights locally; embedding is CPU/GPU-bound rather than network-bound.
- If embedding quality or speed becomes a bottleneck later, swapping to a hosted embeddings API only requires changing `Embedder`, not any other module.
