"""
Tests for geoafrica.datasets.satellite
"""
import pytest
from unittest.mock import patch, MagicMock


@patch("pystac_client.Client.open")
def test_search(mock_client_open):
    from geoafrica.datasets.satellite import search
    import pystac

    mock_client = MagicMock()
    mock_search = MagicMock()
    
    # Mock item
    mock_item = MagicMock(spec=pystac.Item)
    mock_item.id = "S2_fake_item"
    
    # Setup mock chain
    mock_search.item_collection.return_value = [mock_item]
    mock_client.search.return_value = mock_search
    mock_client_open.return_value = mock_client

    items = search(
        collection="sentinel-2-l2a",
        bbox=[3.0, 4.0, 4.0, 5.0],
        limit=1
    )
    
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0].id == "S2_fake_item"


@patch("pystac_client.Client.open")
def test_deafrica_products(mock_client_open):
    from geoafrica.datasets.satellite import deafrica_products
    
    mock_client = MagicMock()
    mock_col1 = MagicMock()
    mock_col1.id = "s2_l2a"
    mock_col1.title = "Sentinel 2"
    mock_client.get_collections.return_value = [mock_col1]
    mock_client_open.return_value = mock_client

    df = deafrica_products()
    assert not df.empty
    assert df["id"].iloc[0] == "s2_l2a"
