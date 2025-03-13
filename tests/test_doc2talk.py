"""
Test module for Doc2Talk facade
"""

import asyncio
import os
from pathlib import Path

import pytest

from doc2talk import Doc2Talk


def test_basic_usage():
    """Test basic usage of Doc2Talk facade"""
    # Use a temporary location for testing
    tmp_dir = Path(os.path.dirname(__file__)) / ".." / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    # Create a Doc2Talk instance with minimal configuration (use cache)
    doc2talk = Doc2Talk(cache_id="test_cache")
    
    # Get session ID
    assert doc2talk.session_id is not None
    
    # Chat with non-streaming
    response = doc2talk.chat("What is the core functionality of the project?")
    assert isinstance(response, str)
    assert len(response) > 0
    
    # Verify message history updated
    assert len(doc2talk.messages) == 2
    assert doc2talk.messages[0]["role"] == "user"
    assert doc2talk.messages[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_async_usage():
    """Test async usage of Doc2Talk facade"""
    # Create a Doc2Talk instance
    doc2talk = Doc2Talk(cache_id="test_cache")
    
    # Chat with async non-streaming
    response = await doc2talk.chat_async("How do I use the library?")
    assert isinstance(response, str)
    assert len(response) > 0
    
    # Test streaming response
    chunks = []
    async for chunk in doc2talk.chat_stream_async("Tell me about the project architecture"):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert "".join(chunks)


def test_index_management():
    """Test index building and loading"""
    # Use a temporary location for testing
    tmp_dir = Path(os.path.dirname(__file__)) / ".." / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    # Path for test index
    test_index_path = tmp_dir / "test_index.c4ai"
    
    # Create a Doc2Talk instance and build index
    doc2talk = Doc2Talk(cache_id="test_cache")
    doc2talk.build_index(save_path=test_index_path)
    
    # Verify index created
    assert test_index_path.exists()
    
    # Load from index
    doc2talk_loaded = Doc2Talk.from_index(test_index_path)
    
    # Verify loaded instance works
    response = doc2talk_loaded.chat("What is the purpose of this library?")
    assert isinstance(response, str)
    assert len(response) > 0


def test_session_management():
    """Test session management functionality"""
    # Create a Doc2Talk instance
    doc2talk = Doc2Talk(cache_id="test_cache")
    
    # Get current session ID
    session_id = doc2talk.session_id
    
    # Add a message
    doc2talk.chat("This is a test message")
    
    # List sessions
    sessions = Doc2Talk.list_sessions()
    assert len(sessions) > 0
    
    # Create a new instance with the same session ID
    doc2talk2 = Doc2Talk(session_id=session_id, cache_id="test_cache")
    
    # Verify message history loaded
    assert len(doc2talk2.messages) > 0
    
    # Cleanup the session
    Doc2Talk.delete_session(session_id)