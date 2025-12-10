import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.tools.db_client import DatabaseClient

@pytest.mark.asyncio
async def test_db_client_search():
    """Test database client search functionality"""
    
    # Mock the gRPC stub
    mock_stub = MagicMock()
    mock_response = MagicMock()
    mock_response.items = []
    mock_response.source = "db"
    mock_stub.SearchDates.return_value = mock_response
    
    # Create client and inject mock
    client = DatabaseClient()
    client.stub = mock_stub
    
    # Test search
    result = await client.search_dates_db(
        city="Ottawa",
        category="Romantic",
        max_price_tier=2
    )
    
    # Verify
    assert result["source"] == "db"
    assert result["items"] == []
    mock_stub.SearchDates.assert_called_once()

@pytest.mark.asyncio
async def test_db_client_connection_error():
    """Test database client handles connection errors"""
    
    client = DatabaseClient()
    client.stub = None  # Simulate connection failure
    
    result = await client.search_dates_db(city="Ottawa")
    
    assert "error" in result
    assert result["items"] == []
