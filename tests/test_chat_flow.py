import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from server.chat_handler import ChatHandler

@pytest.mark.asyncio
async def test_chat_flow():
    """Test the basic chat flow"""
    
    # Mock dependencies
    with patch('server.chat_handler.get_db_client') as mock_db, \
         patch('server.chat_handler.get_web_client') as mock_web, \
         patch('server.chat_handler.LLMEngine') as mock_llm_class:
        
        # Setup mocks
        mock_db_client = AsyncMock()
        mock_db_client.search_dates_db.return_value = {
            "items": [
                {
                    "title": "Test Date Idea",
                    "description": "A test date idea",
                    "categories": ["Romantic"],
                    "price_tier": 2,
                    "city": "Ottawa"
                }
            ],
            "source": "db"
        }
        mock_db.return_value = mock_db_client
        
        mock_web_client = AsyncMock()
        mock_web_client.web_search.return_value = {
            "results": []
        }
        mock_web.return_value = mock_web_client
        
        mock_llm = AsyncMock()
        mock_llm.run_chat.return_value = iter(["Here are some great date ideas for you!"])
        mock_llm.parse_structured_answer.return_value = {
            "summary": "Great date options",
            "options": [
                {
                    "title": "Test Date",
                    "categories": ["Romantic"],
                    "price": "$$",
                    "duration_min": 120,
                    "why_it_fits": "Perfect for your needs",
                    "logistics": "Easy to get to",
                    "website": "https://example.com",
                    "source": "db",
                    "citations": []
                }
            ]
        }
        mock_llm_class.return_value = mock_llm
        
        # Create handler
        handler = ChatHandler()
        
        # Test that the handler is created successfully
        assert handler is not None
        assert handler.llm_engine is not None

@pytest.mark.asyncio
async def test_structured_answer_extraction():
    """Test structured answer extraction"""
    
    with patch('server.chat_handler.get_db_client'), \
         patch('server.chat_handler.get_web_client'), \
         patch('server.chat_handler.LLMEngine') as mock_llm_class:
        
        mock_llm = MagicMock()
        mock_llm.parse_structured_answer.return_value = {
            "summary": "Test summary",
            "options": []
        }
        mock_llm_class.return_value = mock_llm
        
        handler = ChatHandler()
        
        # Test extraction
        result = handler._extract_structured_answer("Some response text")
        
        # Verify the method was called
        mock_llm.parse_structured_answer.assert_called_once_with("Some response text")
