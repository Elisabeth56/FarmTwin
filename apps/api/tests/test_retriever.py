import struct

import pytest
from sqlalchemy import text

from app.db.migrate import run_migrations
from app.db.session import SessionLocal
from app.rag import retriever

DIM = 384


def unit(axis: int, tilt: float = 0.0) -> list[float]:
    """A unit vector along `axis`, tilted toward axis+1 to set its distance from others."""
    vec = [0.0] * DIM
    vec[axis] = (1 - tilt**2) ** 0.5
    vec[axis + 1] = tilt
    return vec


CHUNKS = [
    # id, crop, title, content, vector
    (1, "cowpea", "Cowpea pests", "Maruca pod borer attacks cowpea flowers.", unit(0)),
    (2, "maize", "Maize pests", "Fall armyworm feeds in the maize whorl.", unit(0, 0.3)),
    (3, "rice", "Rice blast", "Blast is favoured by damp weather.", unit(10)),
]


@pytest.fixture()
def session(monkeypatch):
    run_migrations()
    with SessionLocal() as s:
        cur = s.connection().connection.cursor()
        try:
            cur.execute(
                f"CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_vec USING vec0("
                f"chunk_id INTEGER PRIMARY KEY, embedding FLOAT[{DIM}])"
            )
        except Exception:
            pytest.skip("sqlite-vec is not loadable here")
        for cid, crop, title, content, vec in CHUNKS:
            s.execute(
                text(
                    "INSERT INTO document_chunks (id, source_id, crop, chunk_title, content) "
                    "VALUES (:id, 's', :crop, :title, :content)"
                ),
                {"id": cid, "crop": crop, "title": title, "content": content},
            )
            cur.execute(
                "INSERT INTO document_chunks_vec(chunk_id, embedding) VALUES (?, ?)",
                (cid, struct.pack(f"{DIM}f", *vec)),
            )
            cur.execute(
                "INSERT INTO document_chunks_fts(rowid, chunk_title, content) VALUES (?, ?, ?)",
                (cid, title, content),
            )
        yield s
        s.rollback()


def ask(session, monkeypatch, vec, query="pests", crops=None):
    monkeypatch.setattr(retriever, "embed_query", lambda _: vec)
    return retriever.retrieve(query, crops, top_k=6, db_session=session)


def test_crop_filter_keeps_other_crops_out(session, monkeypatch):
    result = ask(session, monkeypatch, unit(0), crops=["maize"])
    assert [c["chunk_id"] for c in result.chunks] == [2]


def test_intercropped_farm_searches_both_crops(session, monkeypatch):
    result = ask(session, monkeypatch, unit(0), crops=["maize", "cowpea"])
    assert {c["chunk_id"] for c in result.chunks} == {1, 2}


def test_keyword_match_lifts_a_chunk_the_vectors_rank_lower(session, monkeypatch):
    # both chunks are near in vector space; only the maize one mentions armyworm
    result = ask(session, monkeypatch, unit(0, 0.05), query="armyworm", crops=["maize", "cowpea"])
    assert result.chunks[0]["chunk_id"] == 2


def test_nothing_close_enough_is_refused(session, monkeypatch):
    result = ask(session, monkeypatch, unit(100), query="cocoa pruning")
    assert result.refused
    assert result.best_distance is not None and result.best_distance > 1


def test_fts_terms_cannot_inject_syntax():
    assert retriever._fts_terms('beans" OR NOT x* (cowpea)') == '"beans" OR "not" OR "cowpea"'
