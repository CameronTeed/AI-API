"""
Integration tests for refactored AI Orchestrator
Tests that all components work together correctly
"""

import pytest
import asyncio
from typing import Dict, Any


class TestMLIntegration:
    """Test ML service integration"""
    
    @pytest.mark.asyncio
    async def test_ml_wrapper_initialization(self):
        """Test ML wrapper initializes correctly"""
        from server.core.ml_integration import get_ml_wrapper
        
        ml_wrapper = get_ml_wrapper()
        assert ml_wrapper is not None
        assert hasattr(ml_wrapper, 'predict_vibe')
        assert hasattr(ml_wrapper, 'plan_date')
    
    @pytest.mark.asyncio
    async def test_vibe_prediction(self):
        """Test vibe prediction works"""
        from server.core.ml_integration import get_ml_wrapper
        
        ml_wrapper = get_ml_wrapper()
        vibe = ml_wrapper.predict_vibe("Romantic dinner")
        
        assert vibe is not None
        assert isinstance(vibe, str)
        assert len(vibe) > 0


class TestSearchEngineIntegration:
    """Test search engine integration"""
    
    @pytest.mark.asyncio
    async def test_search_engine_initialization(self):
        """Test search engine initializes correctly"""
        from server.core.search_engine import get_search_engine
        
        search_engine = get_search_engine()
        assert search_engine is not None
        assert hasattr(search_engine, 'semantic_search')
        assert hasattr(search_engine, 'web_search')
        assert hasattr(search_engine, 'vibe_filtered_search')
    
    @pytest.mark.asyncio
    async def test_semantic_search(self):
        """Test semantic search works"""
        from server.core.search_engine import get_search_engine
        
        search_engine = get_search_engine()
        results = await search_engine.semantic_search("romantic dinner", limit=5)
        
        assert isinstance(results, list)


class TestEnhancedLLMEngine:
    """Test enhanced LLM engine"""
    
    @pytest.mark.asyncio
    async def test_llm_engine_initialization(self):
        """Test LLM engine initializes"""
        from server.llm.engine import get_llm_engine

        engine = get_llm_engine()
        assert engine is not None
        assert hasattr(engine, 'run_chat')
        assert hasattr(engine, 'ml_wrapper')
        assert hasattr(engine, 'search_engine')


class TestEnhancedAgentTools:
    """Test enhanced agent tools"""
    
    @pytest.mark.asyncio
    async def test_agent_tools_initialization(self):
        """Test agent tools initialize"""
        from server.tools.agent_tools import get_agent_tools

        tools = get_agent_tools()
        assert tools is not None
        assert hasattr(tools, 'vector_search')
        assert hasattr(tools, 'web_search')
        assert hasattr(tools, 'get_tool_list')
        assert hasattr(tools, 'execute_tool')
    
    @pytest.mark.asyncio
    async def test_vector_search(self):
        """Test vector search"""
        from server.tools.agent_tools import get_agent_tools

        tools = get_agent_tools()
        results = await tools.vector_search("romantic dinner", limit=5)
        
        assert isinstance(results, dict)


class TestChatHandler:
    """Test chat handler integration"""
    
    def test_chat_handler_initialization(self):
        """Test chat handler initializes with all components"""
        from server.chat_handler import EnhancedChatHandler
        
        handler = EnhancedChatHandler()
        assert handler is not None
        assert handler.llm_engine is not None
        assert handler.enhanced_llm_engine is not None
        assert handler.vector_store is not None
        assert handler.web_client is not None
        assert handler.agent_tools is not None
        assert handler.ml_wrapper is not None
        assert handler.search_engine is not None
        assert handler.chat_storage is not None


class TestAPIEndpoints:
    """Test API endpoints"""
    
    @pytest.mark.asyncio
    async def test_ml_endpoints_available(self):
        """Test ML endpoints are available"""
        from server.api.ml_endpoints import router
        
        assert router is not None
        # Check that routes are registered
        routes = [route.path for route in router.routes]
        assert any('/vibe/predict' in route for route in routes)
        assert any('/plan/date' in route for route in routes)
        assert any('/search/integrated' in route for route in routes)
        assert any('/plan/comprehensive' in route for route in routes)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

