# ADR-016: Embeddings with fastembed (ONNX), bundled in the installer

- Status: Accepted
- Date: 2026-11-11

## Context
v1 used sentence-transformers, which pulls in PyTorch and downloads its model from Hugging Face on first load. On a machine that was never online, retrieval fails. PyTorch also bloats the frozen backend for every OS and competes with llama.cpp for 8GB of RAM.

## Options
- **sentence-transformers.** Current; PyTorch dependency and a runtime download.
- **A second llama-server instance with a GGUF embedding model.** No PyTorch, but another sidecar, port, and lifecycle to manage.
- **fastembed.** ONNX Runtime, in-process, no PyTorch.

## Decision
fastembed with `BAAI/bge-small-en-v1.5`. Model files ship inside the installer and are loaded from a local path, never fetched at runtime.

## Consequences
- Changing the embedder invalidates v1's vectors and retrieval numbers. Re-ingest the corpus and re-run the retrieval eval (ADR-024) before accepting the change.
- The same embedder must be used at ingest time and query time; the model name is stored with the index and checked at startup.
