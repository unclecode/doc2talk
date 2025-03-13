#!/usr/bin/env python
"""
Main entry point for the doc2talk CLI
"""

import asyncio
from .cli import main

def main_entry_point():
    """Entry point for console_scripts"""
    asyncio.run(main())

if __name__ == "__main__":
    main_entry_point()