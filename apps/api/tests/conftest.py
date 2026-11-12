"""Every test run gets its own empty data folder, so tests never touch real farm data."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def data_dir(tmp_path_factory):
    import os

    path = tmp_path_factory.mktemp("farmtwin-data")
    os.environ["FARMTWIN_DATA_DIR"] = str(path)
    return path


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
