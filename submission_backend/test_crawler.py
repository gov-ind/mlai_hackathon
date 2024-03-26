import numpy as np
import pytest

from crawler import get_data, get_file_path, DEFAULT_SOURCE_INTERVAL, DEFAULT_URL
from energy_db import EnergyDB, TIMESTAMP_COL

def test_crawled_data_contains_expected_intervals():
    """
    Test that the crawled data does not contain duplicate timestamps and
    that it contains timestamps in intervals of 5 minutes.
    """
    db = EnergyDB(file_location=get_file_path())

    df = db.get_data()
    values = df[TIMESTAMP_COL].values
    time_diffs = values[1:] - values[:-1]

    assert np.unique(values).shape[0] == values.shape[0]
    assert (time_diffs == DEFAULT_SOURCE_INTERVAL * 60).all()

@pytest.mark.skip(reason="So that we don't hit the API needlessly")
def test_crawled_data_matches_data_returned_by_api():
    """
    Test that the crawled data matches the data returned by the API.
    """
    db = EnergyDB(file_location=get_file_path())

    data_in_db = db.get_data()
    data_from_api = get_data(DEFAULT_URL, DEFAULT_SOURCE_INTERVAL)
    data_from_api[TIMESTAMP_COL] = data_from_api[TIMESTAMP_COL].apply(lambda a: a.timestamp())

    intersecting_timestamps = data_in_db[TIMESTAMP_COL].isin(data_from_api[TIMESTAMP_COL])
    intersecting_timestamps_for_api = data_from_api[TIMESTAMP_COL].isin(data_in_db[TIMESTAMP_COL])

    if np.where(intersecting_timestamps)[0].shape[0] > 0:
        assert (
            data_in_db[intersecting_timestamps][TIMESTAMP_COL].values ==
            data_from_api[intersecting_timestamps_for_api][TIMESTAMP_COL].values
        ).all()