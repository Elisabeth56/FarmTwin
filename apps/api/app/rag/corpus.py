"""Reads the knowledge corpus and works out which chunks ingest has to add or remove."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CorpusChunk:
    frontmatter: dict
    title: str | None
    content: str
    file: str

    @property
    def content_hash(self) -> str:
        """Changes when the text or any metadata changes, so edits get re-embedded."""
        payload = json.dumps(
            {"fm": self.frontmatter, "title": self.title, "content": self.content},
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


def parse_corpus_file(path: Path) -> list[CorpusChunk]:
    """Splits a corpus file into chunks.

    A file is a run of `---`-separated blocks: a YAML frontmatter block with a
    `source_id`, then the chunk body, which may start with `# Chunk: <title>`.
    """
    blocks = [b.strip() for b in path.read_text(encoding="utf-8").split("---")]
    blocks = [b for b in blocks if b]

    chunks: list[CorpusChunk] = []
    i = 0
    while i < len(blocks):
        frontmatter = _frontmatter(blocks[i], path.name)
        if frontmatter is None or i + 1 >= len(blocks):
            i += 1
            continue

        lines = blocks[i + 1].splitlines()
        title = None
        if lines and lines[0].startswith("# Chunk:"):
            title = lines[0].removeprefix("# Chunk:").strip()
            lines = lines[1:]
        chunks.append(CorpusChunk(frontmatter, title, "\n".join(lines).strip(), path.name))
        i += 2
    return chunks


def load_corpus(corpus_dir: Path) -> list[CorpusChunk]:
    return [chunk for path in sorted(corpus_dir.glob("*.md")) for chunk in parse_corpus_file(path)]


def plan_sync(
    existing: dict[int, str | None], chunks: list[CorpusChunk]
) -> tuple[list[CorpusChunk], list[int]]:
    """Returns (chunks to add, row ids to delete) given the stored {row id: hash}.

    Rows without a hash come from the v1 full-rebuild ingester and are replaced.
    Duplicate chunks in the corpus are added once.
    """
    wanted = {chunk.content_hash: chunk for chunk in chunks}
    stored = {h for h in existing.values() if h}
    to_add = [chunk for h, chunk in wanted.items() if h not in stored]
    to_delete = [row_id for row_id, h in existing.items() if h is None or h not in wanted]
    return to_add, to_delete


def _frontmatter(block: str, file: str) -> dict | None:
    if not block.lstrip().startswith("source_id:"):
        return None
    # a broken frontmatter block used to drop its chunk silently; fail loudly instead
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError as exc:
        raise ValueError(f"{file}: bad frontmatter (quote values that contain ': '): {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{file}: frontmatter is not a mapping")
    return data
