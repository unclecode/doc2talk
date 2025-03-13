"""
Simple usage example for Doc2Talk with lazy initialization
"""

import time
from doc2talk import Doc2Talk

print("Creating Doc2Talk instance (fast, no index building yet)...")
start_time = time.time()
doc2talk = Doc2Talk()  # Initialize without building index
creation_time = time.time() - start_time
print(f"Instance created in {creation_time:.4f} seconds")

# Get the session ID for future reference
print(f"Session ID: {doc2talk.session_id}")

# Explicitly build the index before starting to chat
print("\nExplicitly building the index before chatting...")
start_time = time.time()
doc2talk.build_index()  # This builds the index without sending any messages
build_time = time.time() - start_time
print(f"Index built in {build_time:.2f} seconds")

# Now ask a question - the index is already built
question = "How does the crawling system work in the project?"
print(f"\nQuestion: {question}")

print("\nGenerating response (index already built)...")
start_time = time.time()
response = doc2talk.chat(question)
total_time = time.time() - start_time
print(f"Response generated in {total_time:.2f} seconds (with pre-built index)")
print(f"\nResponse:\n{response}")

# Ask another question (index is already built)
follow_up = "What are the main components of the architecture?"
print(f"\nQuestion: {follow_up}")

# Use streaming response
print("\nResponse:")
start_time = time.time()
for chunk in doc2talk.chat_stream(follow_up):
    print(chunk, end="", flush=True)
stream_time = time.time() - start_time
print(f"\nStreaming response completed in {stream_time:.2f} seconds")

# Get context information
print(f"\nContext decision for next question: {doc2talk.get_context_decision('How do I handle rate limiting?')}")

# Example of creating an instance with immediate building
print("\nAlternative: Creating an instance with immediate building...")
start_time = time.time()
doc2talk2 = Doc2Talk(build_immediately=True)
immediate_time = time.time() - start_time
print(f"Instance created and index built in {immediate_time:.2f} seconds")