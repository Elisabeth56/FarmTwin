import pytest
from pydantic import ValidationError

from app.config import Settings


def test_database_lives_in_the_data_folder(data_dir):
    settings = Settings()
    assert settings.database_path == data_dir / "farmtwin.db"


def test_unwritable_data_folder_fails_with_a_clear_message(tmp_path):
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("")
    with pytest.raises(ValidationError, match="can't write to its data folder"):
        Settings(data_dir=blocker / "inside")


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_and_list_farm(client):
    created = client.post("/api/farms", json={"name": "Adamu's farm", "region": "Zaria"})
    assert created.status_code == 201
    names = [f["name"] for f in client.get("/api/farms").json()]
    assert "Adamu's farm" in names
