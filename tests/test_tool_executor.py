"""
Tests for the tool executor
"""

import pytest
import asyncio
from server.tools.tool_executor import ToolExecutor, get_tool_executor


@pytest.fixture
def executor():
    """Create tool executor"""
    return ToolExecutor(max_workers=3)


def test_parallel_execution(executor):
    """Test parallel execution of tools"""

    async def run_test():
        async def tool1():
            await asyncio.sleep(0.1)
            return {"result": "tool1"}

        async def tool2():
            await asyncio.sleep(0.1)
            return {"result": "tool2"}

        async def tool3():
            await asyncio.sleep(0.1)
            return {"result": "tool3"}

        tools = [
            {"name": "tool1", "func": tool1, "args": {}},
            {"name": "tool2", "func": tool2, "args": {}},
            {"name": "tool3", "func": tool3, "args": {}},
        ]

        results = await executor.execute_parallel(tools, timeout=5.0)

        assert len(results) == 3
        assert "tool1" in results
        assert "tool2" in results
        assert "tool3" in results
        assert results["tool1"]["result"] == "tool1"

    asyncio.run(run_test())


def test_sequential_execution(executor):
    """Test sequential execution of tools"""

    async def run_test():
        execution_order = []

        async def tool1():
            execution_order.append(1)
            await asyncio.sleep(0.05)
            return {"result": "tool1"}

        async def tool2():
            execution_order.append(2)
            await asyncio.sleep(0.05)
            return {"result": "tool2"}

        tools = [
            {"name": "tool1", "func": tool1, "args": {}},
            {"name": "tool2", "func": tool2, "args": {}},
        ]

        results = await executor.execute_sequential(tools, timeout=5.0)

        assert len(results) == 2
        assert execution_order == [1, 2]

    asyncio.run(run_test())


def test_tool_timeout(executor):
    """Test tool timeout handling"""

    async def run_test():
        async def slow_tool():
            await asyncio.sleep(5.0)
            return {"result": "should_timeout"}

        tools = [
            {"name": "slow_tool", "func": slow_tool, "args": {}},
        ]

        results = await executor.execute_parallel(tools, timeout=0.1)

        assert "slow_tool" in results
        assert "error" in results["slow_tool"]

    asyncio.run(run_test())


def test_tool_error_handling(executor):
    """Test error handling in tool execution"""

    async def run_test():
        async def failing_tool():
            raise ValueError("Tool failed")

        tools = [
            {"name": "failing_tool", "func": failing_tool, "args": {}},
        ]

        results = await executor.execute_parallel(tools, timeout=5.0)

        assert "failing_tool" in results
        assert "error" in results["failing_tool"]

    asyncio.run(run_test())


def test_cache_key_generation(executor):
    """Test cache key generation"""
    
    key1 = executor.get_cache_key("tool1", {"arg1": "value1"})
    key2 = executor.get_cache_key("tool1", {"arg1": "value1"})
    key3 = executor.get_cache_key("tool1", {"arg1": "value2"})
    
    assert key1 == key2
    assert key1 != key3


def test_result_caching(executor):
    """Test result caching"""
    
    result = {"data": "test"}
    executor.cache_result("tool1", {"arg": "value"}, result)
    
    cached = executor.get_cached_result("tool1", {"arg": "value"})
    assert cached == result


def test_cache_expiration(executor):
    """Test cache expiration"""
    
    executor._cache_ttl = 0.1  # Very short TTL
    result = {"data": "test"}
    executor.cache_result("tool1", {"arg": "value"}, result)
    
    # Should be cached immediately
    cached = executor.get_cached_result("tool1", {"arg": "value"})
    assert cached == result
    
    # Wait for expiration
    asyncio.run(asyncio.sleep(0.2))
    
    # Should be expired
    cached = executor.get_cached_result("tool1", {"arg": "value"})
    assert cached is None


def test_cache_clearing(executor):
    """Test cache clearing"""
    
    executor.cache_result("tool1", {"arg": "value"}, {"data": "test"})
    executor.clear_cache()
    
    cached = executor.get_cached_result("tool1", {"arg": "value"})
    assert cached is None


def test_global_executor_instance():
    """Test global executor instance"""
    
    executor1 = get_tool_executor()
    executor2 = get_tool_executor()
    
    assert executor1 is executor2

