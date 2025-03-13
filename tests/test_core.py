"""
Test script for doc2talk core functionality
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path for importing the package
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.doc2talk.core import ChatEngine, ChatSession


async def test_basic_question():
    """Test a basic question about the crawl4ai codebase"""

    print("Creating chat session...")
    session = ChatSession()

    # Initialize chat engine with GitHub repositories
    print("Initializing chat engine...")
    engine = ChatEngine(
        code_source="https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        docs_source="https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2",
        # force_rebuild=True,
    )

    # Ask a simple question
    question = "How does the crawl4ai extractor functionality work?"
    question = """As an Crawl4ai Experts, answer this question a user asked in our discord.
    
```
I have 1000 company websites with different domains. each different html structure. I need an ai agent to crawl each website for a bit and decide whether this company offers a specific product/service or not. is crawl4ai a good idea?
```

The answer is yes 100%, what we do is we use LLMExtractionStrategy where for scheme we use pydantic to create an schema,  which is the result of LLM judgment about whetehr the link provide that offer or not. We try to use many of our technique to reduce the size of markdown, excluding tags doesn have anything to this, use prunning filter and more, then we use run_many and collected all extracted_content  to know which urls passed.
I need you to generate the minimal code to show the user the idea and also add a concise explanation"""
    session.add_message("user", question)

    print(f"\nUser: {question}")
    print("\nThinking...\n")

    # Get the answer (non-streaming)
    answer = await engine.respond(session, question)

    print(f"DocTalk: {answer}")

    # Print context status
    status = session.context_manager.get_status()
    print("\nContext Status:")
    print(f"- Number of contexts: {status['context_count']}")
    print(f"- Token count: {status['token_count']}")
    print(f"- Last action: {status['action']}")

    return answer

async def test_streaming_response():
    """Test streaming response functionality"""

    print("Creating chat session...")
    session = ChatSession()

    # Initialize chat engine with GitHub repositories
    print("Initializing chat engine...")
    engine = ChatEngine(
        code_source="https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        docs_source="https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2",
    )

    # Ask a simple question
    question = "What are the main components of crawl4ai architecture?"
    session.add_message("user", question)

    print(f"\nUser: {question}")
    print("\nDocTalk: ", end="", flush=True)

    # Update context first
    decision = await engine.get_context_decision(session, question)
    await engine.update_context(session, question, decision)

    # Get streaming response
    async for chunk in engine.generate_response_stream(session, question):
        print(chunk, end="", flush=True)

    print("\n")

    # Print context status
    status = session.context_manager.get_status()
    print("\nContext Status:")
    print(f"- Number of contexts: {status['context_count']}")
    print(f"- Token count: {status['token_count']}")
    print(f"- Last action: {status['action']}")

if __name__ == "__main__":
    # Run the test
    print("Testing doc2talk core functionality...")
    print("=" * 50)

    # # Choose test function
    # test_streaming = len(sys.argv) > 1 and sys.argv[1] == "--stream"

    # if test_streaming:
    #     asyncio.run(test_streaming_response())
    # else:
    #     asyncio.run(test_basic_question())

    # asyncio.run(test_basic_question())
    asyncio.run(test_streaming_response())
