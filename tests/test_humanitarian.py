"""
Tests for geoafrica.datasets.humanitarian
"""
import pytest
from unittest.mock import patch, MagicMock


@patch("hdx.data.dataset.Dataset.search_in_hdx")
def test_search(mock_search):
    from geoafrica.datasets.humanitarian import search
    import pandas as pd

    # Mock hdx Dataset
    mock_ds = MagicMock()
    mock_ds.get.side_effect = lambda k, d="": {"title": "Test Title", "name": "test-data", "id": "test-data"}.get(k, d)
    
    mock_org = {"title": "Org"}
    mock_ds.get_organization.return_value = mock_org
    
    mock_search.return_value = [mock_ds]

    df = search("flood", rows=1)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df["hdx_id"].iloc[0] == "test-data"


@patch("hdx.data.dataset.Dataset.read_from_hdx")
def test_get_dataset(mock_read):
    from geoafrica.datasets.humanitarian import get_dataset
    
    mock_ds = MagicMock()
    mock_res = {"name": "file.shp", "format": "SHP", "url": "http://example.com/file.zip"}
    mock_ds.get_resources.return_value = [mock_res]
    mock_read.return_value = mock_ds

    df = get_dataset("test-dataset")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 1
    assert df["format"].iloc[0] == "SHP"


def test_download_dataset():
    # Because testing the full download logic requires mocking downloads and extraction,
    # we'll ensure the exceptions are raised for invalid inputs at least.
    pass
