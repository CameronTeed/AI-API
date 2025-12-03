"""
Optimized Tool Executor for parallel execution of agent tools
Efficiently manages tool execution with caching and parallel processing
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Manages efficient execution of tools with parallel processing"""
    
    def __init__(self, max_workers: int = 5):
        """
        Initialize the tool executor
        
        Args:
            max_workers: Maximum number of concurrent tool executions
        """
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._execution_cache = {}
        self._cache_ttl = 300  # 5 minutes
        logger.info(f"🔧 ToolExecutor initialized with {max_workers} workers")
    
    async def execute_parallel(
        self,
        tools: List[Dict[str, Any]],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Execute multiple tools in parallel
        
        Args:
            tools: List of tool definitions with 'name' and 'func' keys
            timeout: Timeout for each tool execution in seconds
        
        Returns:
            Dictionary with tool results
        """
        logger.info(f"⚡ Executing {len(tools)} tools in parallel")
        
        tasks = []
        for tool in tools:
            tool_name = tool.get('name', 'unknown')
            tool_func = tool.get('func')
            tool_args = tool.get('args', {})
            
            if not tool_func:
                logger.warning(f"⚠️ Tool {tool_name} has no function")
                continue
            
            # Create task with timeout
            task = asyncio.create_task(
                self._execute_with_timeout(tool_name, tool_func, tool_args, timeout)
            )
            tasks.append((tool_name, task))
        
        # Gather results
        results = {}
        for tool_name, task in tasks:
            try:
                result = await task
                results[tool_name] = result
                logger.debug(f"✅ Tool {tool_name} completed successfully")
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Tool {tool_name} timed out after {timeout}s")
                results[tool_name] = {"error": f"Tool timed out after {timeout}s"}
            except Exception as e:
                logger.error(f"❌ Tool {tool_name} failed: {e}")
                results[tool_name] = {"error": str(e)}
        
        logger.info(f"✅ Parallel execution completed: {len(results)}/{len(tools)} tools succeeded")
        return results
    
    async def _execute_with_timeout(
        self,
        tool_name: str,
        tool_func: Callable,
        tool_args: Dict[str, Any],
        timeout: float
    ) -> Any:
        """Execute a tool with timeout"""
        start_time = time.time()
        
        try:
            # Check if function is async
            if asyncio.iscoroutinefunction(tool_func):
                result = await asyncio.wait_for(
                    tool_func(**tool_args),
                    timeout=timeout
                )
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(self.executor, tool_func, **tool_args),
                    timeout=timeout
                )
            
            elapsed = time.time() - start_time
            logger.debug(f"⏱️ Tool {tool_name} completed in {elapsed:.2f}s")
            return result
        
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            raise
    
    async def execute_sequential(
        self,
        tools: List[Dict[str, Any]],
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Execute tools sequentially (useful when order matters)
        
        Args:
            tools: List of tool definitions
            timeout: Timeout for each tool execution
        
        Returns:
            Dictionary with tool results
        """
        logger.info(f"📊 Executing {len(tools)} tools sequentially")
        
        results = {}
        for tool in tools:
            tool_name = tool.get('name', 'unknown')
            tool_func = tool.get('func')
            tool_args = tool.get('args', {})
            
            if not tool_func:
                logger.warning(f"⚠️ Tool {tool_name} has no function")
                continue
            
            try:
                result = await self._execute_with_timeout(tool_name, tool_func, tool_args, timeout)
                results[tool_name] = result
                logger.debug(f"✅ Tool {tool_name} completed")
            except Exception as e:
                logger.error(f"❌ Tool {tool_name} failed: {e}")
                results[tool_name] = {"error": str(e)}
        
        logger.info(f"✅ Sequential execution completed: {len(results)}/{len(tools)} tools succeeded")
        return results
    
    def get_cache_key(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Generate cache key for tool execution"""
        import hashlib
        import json
        
        key_str = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get_cached_result(self, tool_name: str, args: Dict[str, Any]) -> Optional[Any]:
        """Get cached result if available and not expired"""
        cache_key = self.get_cache_key(tool_name, args)
        
        if cache_key in self._execution_cache:
            cached_data = self._execution_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                logger.debug(f"💾 Cache hit for {tool_name}")
                return cached_data['result']
            else:
                # Cache expired
                del self._execution_cache[cache_key]
        
        return None
    
    def cache_result(self, tool_name: str, args: Dict[str, Any], result: Any) -> None:
        """Cache tool execution result"""
        cache_key = self.get_cache_key(tool_name, args)
        self._execution_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        logger.debug(f"💾 Cached result for {tool_name}")
    
    def clear_cache(self) -> None:
        """Clear all cached results"""
        self._execution_cache.clear()
        logger.info("🧹 Tool execution cache cleared")
    
    def close(self) -> None:
        """Close the executor"""
        self.executor.shutdown(wait=True)
        logger.info("🔌 ToolExecutor closed")


# Global instance
_tool_executor = None


def get_tool_executor(max_workers: int = 5) -> ToolExecutor:
    """Get global tool executor instance"""
    global _tool_executor
    if _tool_executor is None:
        _tool_executor = ToolExecutor(max_workers=max_workers)
    return _tool_executor

