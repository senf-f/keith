import pytest

from keith.db import Database


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "keith.db")
    yield database
    database.close()
