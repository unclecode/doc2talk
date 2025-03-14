"""
Simple usage example for Doc2Talk
"""

from doc2talk import Doc2Talk

print("Creating Doc2Talk instance...")
doc2talk = Doc2Talk(
    code_source="https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
    docs_source="https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2",
)  # Initialize without building index

# Get the session ID for future reference
print(f"Session ID: {doc2talk.session_id}")

# Explicitly build the index before starting to chat (optional)
print("\nBuilding index before chatting...")
doc2talk.build_index()  # This builds the index without sending any messages
print("Index built successfully")

# Ask a question
question = "How does the crawling system work in the project?"
print(f"\nQuestion: {question}")
response = doc2talk.chat(question)
print(f"\nResponse:\n{response}")

# Ask a follow-up question
follow_up = "What are the main components of the architecture?"
print(f"\nQuestion: {follow_up}")

# Use streaming response - each chunk is yielded as it arrives
print("\nResponse (streaming):")
for chunk in doc2talk.chat_stream(follow_up):
    print(chunk, end="", flush=True)
print("\n")

# Get context information
context_decision = doc2talk.get_context_decision("How do I handle rate limiting?")
print(f"\nContext decision for next question: {context_decision}")

# Alternative approach - create an instance with immediate building
print("\nAlternative: Creating an instance with immediate building...")
doc2talk2 = Doc2Talk(build_immediately=True)
print("Instance created with index built during initialization")
