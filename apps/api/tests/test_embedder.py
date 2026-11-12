import os

import pytest

from app.config import get_settings
from app.errors import AppError
from app.rag import embedder


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
