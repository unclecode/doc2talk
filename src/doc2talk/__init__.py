"""
Doc2Talk - A tool for chatting with your code and documentation
"""

__version__ = "0.1.0"

# Export main facade class for simple usage
from .doc2talk import Doc2Talk

# Export core classes for advanced programmatic use
from .core import (
    ChatSession,
    SessionManager,
    ContextManager,
    ChatEngine
)

# Export CLI entry point
from .cli import main as cli_main

