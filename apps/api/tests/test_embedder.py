import os

import pytest

from app.config import get_settings
from app.db import models
from app.db.migrate import run_migrations
from app.db.session import SessionLocal
from app.errors import AppError
from app.rag import embedder
from app.rag.index_meta import IndexMismatchError, check_index_embedder, record_embedder


@pytest.fixture()
def session():
    run_migrations()
    with SessionLocal() as s:
        yield s
        s.rollback()


def add_chunk(session):
    session.add(models.DocumentChunk(source_id="s", content="text", content_hash="h"))
    session.flush()


def test_empty_index_passes_the_check(session):
    check_index_embedder(session)


def test_index_built_with_the_configured_embedder_passes(session):
    add_chunk(session)
    record_embedder(session, get_settings().embedder_model)
    check_index_embedder(session)


def test_index_built_with_another_embedder_fails_with_a_clear_message(session):
    add_chunk(session)
    record_embedder(session, "all-MiniLM-L6-v2")
    with pytest.raises(IndexMismatchError, match="all-MiniLM-L6-v2.*scripts/ingest.py"):
        check_index_embedder(session)


def test_v1_index_without_a_recorded_embedder_fails(session):
    add_chunk(session)
    with pytest.raises(IndexMismatchError, match="older version"):
        check_index_embedder(session)


def test_missing_model_files_raise_a_plain_error(monkeypatch, tmp_path):
    monkeypatch.setattr(embedder, "_model", None)
    monkeypatch.setattr(get_settings(), "embedder_dir", tmp_path)
    with pytest.raises(AppError) as err:
        embedder.get_model()
    assert err.value.code == embedder.EMBEDDER_MISSING


@pytest.mark.skipif(
    not os.environ.get("FARMTWIN_EMBEDDER_DIR"), reason="needs the embedder on disk (CI fetches it)"
)
def test_embeds_offline():
    os.environ["HF_HUB_OFFLINE"] = "1"
    vec = embedder.embed_query("when should I spray cowpea against Maruca?")
    assert len(vec) == 384
    passages = embedder.embed_passages(["Maruca attacks cowpea at flowering.", "Yam is staked."])
    sims = [sum(a * b for a, b in zip(vec, p, strict=True)) for p in passages]
    assert sims[0] > sims[1]
