from pathlib import Path

import pytest

from app.config import get_settings
from app.rag.corpus import CorpusChunk, load_corpus, parse_corpus_file, plan_sync

KNOWLEDGE = get_settings().knowledge_dir
REQUIRED = {"source_id", "source_title", "source_org", "source_url", "crop", "topics"}
CROPS = {"maize", "cassava", "yam", "sorghum", "rice", "cowpea"}


@pytest.fixture(scope="module")
def corpus() -> list[CorpusChunk]:
    return load_corpus(KNOWLEDGE / "corpus")


def test_every_chunk_has_the_metadata_retrieval_needs(corpus):
    for chunk in corpus:
        missing = REQUIRED - chunk.frontmatter.keys()
        assert not missing, f"{chunk.file} '{chunk.title}' is missing {missing}"
        assert chunk.content, f"{chunk.file} '{chunk.title}' has no body"


def test_every_source_is_listed_in_sources_md(corpus):
    listed = (KNOWLEDGE / "SOURCES.md").read_text()
    for chunk in corpus:
        assert f"`{chunk.frontmatter['source_id']}`" in listed, chunk.frontmatter["source_id"]


def test_every_supported_crop_has_chunks(corpus):
    crops = {chunk.frontmatter["crop"] for chunk in corpus}
    assert CROPS <= crops


def test_parse_reads_title_and_body(tmp_path: Path):
    path = tmp_path / "x.md"
    path.write_text("---\nsource_id: s\ncrop: yam\n---\n\n# Chunk: Hello\n\nBody text.\n\n---\n")
    [chunk] = parse_corpus_file(path)
    assert chunk.title == "Hello"
    assert chunk.content == "Body text."
    assert chunk.frontmatter == {"source_id": "s", "crop": "yam"}


def _chunk(content: str, crop: str = "yam") -> CorpusChunk:
    return CorpusChunk({"source_id": "s", "crop": crop}, "t", content, "f.md")


def test_hash_changes_with_text_or_metadata():
    assert _chunk("a").content_hash == _chunk("a").content_hash
    assert _chunk("a").content_hash != _chunk("b").content_hash
    assert _chunk("a").content_hash != _chunk("a", crop="rice").content_hash


def test_sync_adds_only_new_and_removes_stale():
    keep, edited, new = _chunk("keep"), _chunk("edited v2"), _chunk("new")
    existing = {1: keep.content_hash, 2: _chunk("edited v1").content_hash, 3: None}
    to_add, to_delete = plan_sync(existing, [keep, edited, new])
    assert {c.content for c in to_add} == {"edited v2", "new"}
    assert sorted(to_delete) == [2, 3]


def test_second_sync_is_a_no_op():
    chunks = [_chunk("a"), _chunk("b")]
    to_add, _ = plan_sync({}, chunks)
    existing = {i: c.content_hash for i, c in enumerate(to_add)}
    assert plan_sync(existing, chunks) == ([], [])
