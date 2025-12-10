"""
Tests for chat context storage
"""

import pytest
import asyncio
from server.tools.chat_context_storage import ChatContextStorage, get_chat_storage


def test_create_session():
    """Test creating a chat session"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_1"
        user_id = "test_user_1"

        result = await storage.create_session(
            session_id=session_id,
            user_id=user_id,
            metadata={"test": "data"}
        )

        await storage.close()
        assert result is True

    asyncio.run(run_test())


def test_store_message():
    """Test storing a message"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_2"
        await storage.create_session(session_id=session_id)

        message_id = await storage.store_message(
            session_id=session_id,
            role="user",
            content="Hello, how are you?"
        )

        await storage.close()
        assert message_id is not None
        assert isinstance(message_id, int)

    asyncio.run(run_test())


def test_add_message_convenience():
    """Test add_message convenience method"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_3"
        await storage.create_session(session_id=session_id)

        message_id = await storage.add_message(
            session_id=session_id,
            role="assistant",
            content="Hello! I'm doing well."
        )

        await storage.close()
        assert message_id is not None

    asyncio.run(run_test())


def test_get_session_messages():
    """Test retrieving session messages"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_4"
        await storage.create_session(session_id=session_id)

        # Add multiple messages
        await storage.add_message(session_id, "user", "Message 1")
        await storage.add_message(session_id, "assistant", "Response 1")
        await storage.add_message(session_id, "user", "Message 2")

        messages = await storage.get_session_messages(session_id)

        await storage.close()
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Message 1"
        assert messages[1]["role"] == "assistant"

    asyncio.run(run_test())


def test_get_session_messages_with_limit():
    """Test retrieving session messages with limit"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_5"
        await storage.create_session(session_id=session_id)

        # Add multiple messages
        for i in range(5):
            await storage.add_message(session_id, "user", f"Message {i}")

        messages = await storage.get_session_messages(session_id, limit=2)

        await storage.close()
        assert len(messages) == 2

    asyncio.run(run_test())


def test_deactivate_session():
    """Test deactivating a session"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_6"
        await storage.create_session(session_id=session_id)

        result = await storage.deactivate_session(session_id)

        await storage.close()
        assert result is True

    asyncio.run(run_test())


def test_store_tool_call():
    """Test storing a tool call"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_7"
        await storage.create_session(session_id=session_id)

        message_id = await storage.add_message(session_id, "user", "Search for restaurants")

        result = await storage.store_tool_call(
            session_id=session_id,
            message_id=message_id,
            tool_name="google_places_search",
            tool_arguments={"query": "restaurants", "location": "Ottawa"},
            tool_result={"places": []},
            execution_time_ms=150
        )

        await storage.close()
        assert result is True

    asyncio.run(run_test())


def test_get_session_context():
    """Test getting session context"""

    async def run_test():
        storage = ChatContextStorage()
        await storage.ensure_tables_exist()

        session_id = "test_session_8"
        await storage.create_session(session_id=session_id)

        # Add messages
        await storage.add_message(session_id, "user", "Hello")
        await storage.add_message(session_id, "assistant", "Hi there!")

        context = await storage.get_session_context(session_id)

        await storage.close()
        assert "messages" in context
        assert "tool_calls" in context
        assert "summaries" in context
        assert len(context["messages"]) == 2

    asyncio.run(run_test())


def test_global_storage_instance():
    """Test global storage instance"""
    
    storage1 = get_chat_storage()
    storage2 = get_chat_storage()
    
    assert storage1 is storage2

