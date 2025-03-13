"""
DocTalk main module - A library for code documentation chat
"""

import asyncio
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Union

from .core import ChatEngine, ChatSession, SessionManager


class Doc2Talk:
    """
    Main facade class for Doc2Talk library - provides a simple interface for
    code documentation chat functionality.
    """

    def __init__(
        self,
        code_source: Optional[str] = None,
        docs_source: Optional[str] = None,
        exclude_patterns: Optional[List[str]] = None,
        cache_id: Optional[str] = None,
        session_id: Optional[str] = None,
        force_rebuild: bool = False,
        build_immediately: bool = False,
    ):
        """
        Initialize Doc2Talk with optional code and documentation sources.

        Args:
            code_source: Path to code source (local directory or GitHub URL)
            docs_source: Path to documentation source (local directory or GitHub URL)
            exclude_patterns: List of glob patterns to exclude
            cache_id: Custom identifier for the cache file
            session_id: ID of an existing session to continue
            force_rebuild: Force rebuilding the knowledge graph
            build_immediately: Whether to build the index immediately (default: False)
        """
        # Store engine parameters for later initialization
        self._engine_params = {
            "code_source": code_source,
            "docs_source": docs_source,
            "exclude_patterns": exclude_patterns,
            "cache_id": cache_id,
            "force_rebuild": force_rebuild,
        }
        
        # Engine is lazily initialized
        self.engine = None

        # Initialize or load session
        if session_id:
            self.session = SessionManager.load(session_id)
        else:
            self.session = ChatSession()
            
        # Build index immediately if requested
        if build_immediately:
            self.build_index()

    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        return self.session.session_id

    @property
    def messages(self) -> List[Dict]:
        """Get the current session messages."""
        return self.session.messages

    def chat(self, message: str, model: Optional[str] = None) -> str:
        """
        Send a message and get a response (non-streaming).

        Args:
            message: The user message to send
            model: Optional model override

        Returns:
            The assistant's response
        """
        # Ensure engine is initialized
        self._ensure_engine_initialized()
        
        # Add user message
        self.session.add_message("user", message)

        # Get response (run async function in sync context)
        response = asyncio.run(self.engine.respond(self.session, message))

        # Add assistant message
        self.session.add_message("assistant", response)

        # Save session
        SessionManager.save(self.session)

        return response

    async def chat_async(self, message: str, model: Optional[str] = None) -> str:
        """
        Send a message and get a response asynchronously (non-streaming).

        Args:
            message: The user message to send
            model: Optional model override

        Returns:
            The assistant's response
        """
        # Ensure engine is initialized
        self._ensure_engine_initialized()
        
        # Add user message
        self.session.add_message("user", message)

        # Get response
        response = await self.engine.respond(self.session, message)

        # Add assistant message
        self.session.add_message("assistant", response)

        # Save session
        SessionManager.save(self.session)

        return response

    def chat_stream(self, message: str, model: Optional[str] = None) -> List[str]:
        """
        Send a message and get a streaming response (returns chunks in a list).

        Args:
            message: The user message to send
            model: Optional model override

        Returns:
            List of response chunks
        """
        # Ensure engine is initialized
        self._ensure_engine_initialized()
        
        # Add user message
        self.session.add_message("user", message)

        # Get streaming response (gather chunks)
        chunks = []
        for chunk in asyncio.run(self._stream_helper(message)):
            chunks.append(chunk)

        # Add full assistant message
        full_response = "".join(chunks)
        self.session.add_message("assistant", full_response)

        # Save session
        SessionManager.save(self.session)

        return chunks

    async def chat_stream_async(
        self, message: str, model: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and get a streaming response asynchronously.

        Args:
            message: The user message to send
            model: Optional model override

        Yields:
            Response chunks as they become available
        """
        # Ensure engine is initialized
        self._ensure_engine_initialized()
        
        # Add user message
        self.session.add_message("user", message)

        # Collect full response for saving later
        full_response = []

        # Stream the response
        async for chunk in self.engine.generate_response_stream(self.session, message):
            full_response.append(chunk)
            yield chunk

        # Add assistant message with complete response
        self.session.add_message("assistant", "".join(full_response))

        # Save session
        SessionManager.save(self.session)

    async def _stream_helper(self, message: str) -> AsyncGenerator[str, None]:
        """Helper method for streaming in sync contexts."""
        # Ensure engine is initialized
        self._ensure_engine_initialized()
        
        async for chunk in self.engine.generate_response_stream(self.session, message):
            yield chunk

    def get_context_decision(self, question: str) -> str:
        """
        Get the context decision for a question without sending it.

        Args:
            question: The question to get context decision for

        Returns:
            Decision type: "new", "additional", or "none"
        """
        # Ensure engine is initialized
        self._ensure_engine_initialized()
        
        return asyncio.run(self.engine.get_context_decision(self.session, question))

    def get_current_context(self) -> str:
        """
        Get the current context for the session.

        Returns:
            The current context text
        """
        return self.session.context_manager.current_context()

    def _ensure_engine_initialized(self):
        """Ensure the engine is initialized before use."""
        if self.engine is None:
            self.build_index()
    
    def build_index(self, save_path: Optional[Union[str, Path]] = None) -> None:
        """
        Build the knowledge index and optionally save it.
        
        This method initializes the ChatEngine if not already done,
        which may take a few seconds depending on the repository size.

        Args:
            save_path: Optional path to save the index
        """
        # Initialize the chat engine if not already done
        if self.engine is None:
            self.engine = ChatEngine(**self._engine_params)
        
        # Save the index if a path is provided
        if save_path:
            save_path = Path(save_path) if isinstance(save_path, str) else save_path
            self.engine.knowledge_assistant.persist(save_path)

    @classmethod
    def from_index(
        cls, 
        index_path: Union[str, Path], 
        session_id: Optional[str] = None
    ) -> "Doc2Talk":
        """
        Create a Doc2Talk instance from an existing index.

        Args:
            index_path: Path to the index file
            session_id: Optional session ID to continue

        Returns:
            Doc2Talk instance
        """
        # Convert string path to Path if needed
        index_path = Path(index_path) if isinstance(index_path, str) else index_path
        
        # Create an instance with default initialization but don't build the index
        instance = cls()
        
        # Store the index path for later loading
        instance._index_path = index_path
        
        # Add a custom build_index method to this instance that loads from the specified path
        original_build_index = instance.build_index
        
        def custom_build_index(save_path=None):
            if instance.engine is None:
                # Create engine with custom initialization
                instance.engine = ChatEngine.__new__(ChatEngine)
                instance.engine.CACHE_DIR = Path.home() / ".doctalk" / "index"
                
                # Load from the index file
                engine_class = type(instance.engine)
                instance.engine.knowledge_assistant = engine_class.knowledge_assistant.load(instance._index_path)
                
                # Setup other engine attributes needed
                instance.engine.decider = engine_class.decider.__new__(engine_class.decider)
            
            # Handle saving if requested
            if save_path:
                save_path = Path(save_path) if isinstance(save_path, str) else save_path
                instance.engine.knowledge_assistant.persist(save_path)
                
        # Replace the build_index method
        instance.build_index = custom_build_index
        
        # Initialize or load session
        if session_id:
            instance.session = SessionManager.load(session_id)
        else:
            instance.session = ChatSession()
            
        return instance

    @staticmethod
    def list_sessions() -> List[Dict]:
        """
        List all saved sessions.

        Returns:
            List of session information dictionaries
        """
        return SessionManager.list_sessions()

    @staticmethod
    def delete_session(session_id: str) -> bool:
        """
        Delete a specific session.

        Args:
            session_id: ID of the session to delete

        Returns:
            True if successful, False otherwise
        """
        return SessionManager.delete_session(session_id)