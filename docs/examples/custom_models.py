"""
Example demonstrating custom LLM configurations with Doc2Talk
"""

import asyncio
from doc2talk import Doc2Talk
from doc2talk.models import LLMConfig

async def main():
    print("Doc2Talk with Custom LLM Configurations")
    print("======================================\n")

    # Create a custom configuration for decisions (using a cheaper model for decision-making)
    decision_config = LLMConfig(
        model="gpt-4o",  # Use a cheaper model for decision making
        temperature=0.6,        # Lower temperature for more consistent decisions
        max_tokens=200         # Limit token usage for decisions
    )
    
    # Create a custom configuration for response generation (using a strong model)
    generation_config = LLMConfig(
        model="gpt-3.5-turbo",        # Use the more powerful model for responses
        temperature=0.2,        # Higher temperature for more creative responses
        # max_tokens=1000        # Allow longer responses
    )
    
    # Create Doc2Talk instance with custom LLM configurations
    print("Creating Doc2Talk instance with custom LLM configurations...")
    doc2talk = Doc2Talk(        
        code_source="https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        docs_source="https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2",
        decision_llm_config=decision_config,
        generation_llm_config=generation_config
    )
    
    # Build the index
    print("\nBuilding index...")
    doc2talk.build_index()
    print("Index built successfully")
    
    # Ask a first question - this will trigger context decision with cheaper model
    # and then generate a response with the more powerful model
    question = "How does the crawling system work in this project?"
    print(f"\nQuestion: {question}")
    
    response = await doc2talk.chat_async(question)
    print("\nResponse using custom models:")
    print(response)
    
    # Example of using a different model for a specific question
    print("\nUsing different models for a specific question...")
    # Create a custom high-creativity configuration
    creative_config = LLMConfig(
        model="claude-3-5-sonnet-20240620",
        temperature=0.9,
        max_tokens=2000
    )
    
    # Create a new instance with different model configurations
    doc2talk2 = Doc2Talk(
        code_source="https://github.com/unclecode/crawl4ai/tree/main/crawl4ai",
        docs_source="https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2",
        # Low-resource decision model (same as before)
        decision_llm_config=decision_config,
        # More creative generation model for this specific task 
        generation_llm_config=creative_config
    )
    doc2talk2.build_index()
    
    # Ask for a creative explanation
    creative_question = "Explain the architecture of this project as if it were a city."
    print(f"\nCreative question: {creative_question}")
    
    creative_response = await doc2talk2.chat_async(creative_question)
    print("\nResponse using the creative model:")
    print(creative_response)
    
    print("\nDemonstration of streaming with custom models...")
    question3 = "What are the main components of this project?"
    print(f"\nQuestion: {question3}")
    
    print("\nStreaming response:")
    async for chunk in doc2talk.chat_stream_async(question3):
        print(chunk, end="", flush=True)
    print("\n")
    
if __name__ == "__main__":
    asyncio.run(main())