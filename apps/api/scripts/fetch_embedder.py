"""Downloads the embedder into the local model folder. Run once at setup or build time; the app
itself only ever reads the files from disk.

    uv run python scripts/fetch_embedder.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings
from app.rag.embedder import get_model

if __name__ == "__main__":
    get_model(local_files_only=False)
    print(f"{get_settings().embedder_model} ready in {get_settings().embedder_path}")
