from datetime import datetime, timezone
from energy_db import EnergyDB
import pytest

@pytest.fixture
def db():
    return EnergyDB()

def test_energy_db_slicing(db):
    start = datetime(2023, 4, 15, 0, 0, 0, tzinfo=timezone.utc).timestamp()
    end = datetime(2023, 4, 15, 4, 0, 5, tzinfo=timezone.utc).timestamp()

    data = db.get_data(start, end)

    assert len(data) == 48

    start = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp()
    end = datetime(2023, 4, 17, 0, 0, 5, tzinfo=timezone.utc).timestamp()

    data = db.get_data(start, end)
    assert len(data) == 576

def test_earliest_timestamp_is_unix(db):
    earliest = db.earliest_timestamp()
    assert isinstance(earliest, int)

def test_energy_db_allows_from_start(db):
    start = 0
    end = datetime(2023, 4, 15, 4, 0, 5, tzinfo=timezone.utc).timestamp()

    data = db.get_data(start, end)

    assert len(data) == 48