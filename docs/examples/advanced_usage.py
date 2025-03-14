"""
Advanced usage example for Doc2Talk with improved lazy initialization
"""

import asyncio
import time
from pathlib import Path

from doc2talk import Doc2Talk


async def main():
    print("Doc2Talk Advanced Usage Example")
    print("===============================\n")

    print("Approach 1: Explicit index building")
    print("---------------------------------")
    # Create a Doc2Talk instance with custom repositories without building index yet
    print("Creating instance with lazy initialization...")
    start_time = time.time()
    doc2talk = Doc2Talk(
        code_source="https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        docs_source="https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2",
        exclude_patterns=["**/tests/*", "**/__pycache__/*"],
        cache_id="custom_crawl4ai",
        # Customize history and context limits
        max_history=100,  # Keep up to 100 messages (default is 50)
        max_contexts=10,  # Keep up to 10 contexts (default is 5)
    )
    creation_time = time.time() - start_time
    print(f"Instance created in {creation_time:.4f} seconds")
    print(f"Session ID: {doc2talk.session_id}")

    # Explicitly build index before use
    print("\nExplicitly building index before use...")
    start_time = time.time()
    doc2talk.build_index()
    build_time = time.time() - start_time
    print(f"Index built in {build_time:.2f} seconds")
    
    # Use the instance with pre-built index
    print("\nUsing instance with pre-built index...")
    start_time = time.time()
    response = await doc2talk.chat_async("What is the purpose of this library?")
    response_time = time.time() - start_time
    print(f"Response generated in {response_time:.2f} seconds (using pre-built index)")
    print(f"Response length: {len(response)} characters\n")

    print("\nApproach 2: Build and save index for reuse")
    print("----------------------------------------")
    # Build and save the index for later reuse
    print("Building and saving index for later reuse...")
    tmp_path = Path("./tmp/custom_index.c4ai")
    tmp_path.parent.mkdir(exist_ok=True)
    start_time = time.time()
    doc2talk.build_index(save_path=tmp_path)
    save_time = time.time() - start_time
    print(f"Index built and saved in {save_time:.2f} seconds")
    print(f"Index saved to {tmp_path}")

    print("\nApproach 3: Loading from pre-built index")
    print("--------------------------------------")
    # Load from existing index with lazy loading and custom history/context limits
    print("Creating new instance from saved index with custom limits...")
    start_time = time.time()
    doc2talk2 = Doc2Talk.from_index(
        tmp_path,
        max_history=75,  # Keep up to 75 messages
        max_contexts=3,  # Keep only 3 contexts (more focused)
    )
    load_time = time.time() - start_time
    print(f"Instance created in {load_time:.4f} seconds (index not loaded yet)")
    print(f"New session ID: {doc2talk2.session_id}")

    # When first used, it will load the index
    print("\nBuilding index on first use...")
    start_time = time.time()
    doc2talk2.build_index()  # Explicitly build index before chat
    index_load_time = time.time() - start_time
    print(f"Index loaded in {index_load_time:.2f} seconds")

    # Now use the instance with the loaded index - standard response
    print("\nUsing instance with loaded index (standard response)...")
    start_time = time.time()
    response = await doc2talk2.chat_async("How does the project handle rate limiting?")
    loaded_response_time = time.time() - start_time
    print(f"Response generated in {loaded_response_time:.2f} seconds (with loaded index)")
    print(f"Response length: {len(response)} characters")
    
    # Demonstrate asynchronous streaming
    print("\nUsing instance with loaded index (async streaming)...")
    question2 = "What authentication methods are supported?"
    print("Response (async streaming):")
    start_time = time.time()
    async for chunk in doc2talk2.chat_stream_async(question2):
        print(chunk, end="", flush=True)
    async_stream_time = time.time() - start_time
    print(f"\nAsync streaming completed in {async_stream_time:.2f} seconds")
    
    # Demonstrate synchronous streaming
    print("\nUsing instance with loaded index (sync streaming)...")
    question3 = "How do I add a custom crawler?"
    print("Response (sync streaming):")
    start_time = time.time()
    for chunk in doc2talk2.chat_stream(question3):
        print(chunk, end="", flush=True)
    sync_stream_time = time.time() - start_time
    print(f"\nSync streaming completed in {sync_stream_time:.2f} seconds")

    print("\nPerformance Comparison:")
    print("---------------------")
    print(f"Lazy initialization:  {creation_time:.4f}s")
    print(f"Explicit build:       {build_time:.2f}s")
    print(f"Index save:           {save_time:.2f}s")
    print(f"Index load:           {index_load_time:.2f}s")
    print(f"Standard response:    {loaded_response_time:.2f}s")
    print(f"Async streaming:      {async_stream_time:.2f}s")
    print(f"Sync streaming:       {sync_stream_time:.2f}s")

    # Display configuration differences
    print("\nConfiguration Comparison:")
    print("-----------------------")
    print(f"Instance 1: max_history=100, max_contexts=10")
    print(f"Instance 2: max_history=75, max_contexts=3")


if __name__ == "__main__":
    asyncio.run(main())