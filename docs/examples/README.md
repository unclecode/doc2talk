# Doc2Talk

A fast, context-aware code documentation chat interface that provides intelligent responses based on your codebase and documentation.

## Features

- **Knowledge Graph Indexing**: Indexes both code and documentation for comprehensive understanding
- **Smart Context Management**: Intelligently decides when to fetch new context or use existing context
- **Lazy Initialization**: Fast startup with on-demand index building
- **Repository Caching**: Efficiently caches GitHub repositories for faster repeated access
- **Custom LLM Support**: Configure different models for decisions and responses
- **High-Performance Storage**: Uses optimized serialization for 100x faster loading times
- **Terminal UI**: Rich terminal interface with interactive streaming responses
- **Session Management**: Save and restore chat sessions for continuous workflows

## Installation

```bash
# Install from PyPI
pip install doc2talk

# Install from source
git clone https://github.com/unclecode/doc2talk.git
cd doc2talk
pip install -e .
```

## Quick Start

### Command Line Interface

```bash
# Specify code and documentation sources (required)
doc2talk --code /path/to/code --docs /path/to/docs

# Use a GitHub repository
doc2talk --code https://github.com/unclecode/doc2talk/tree/main/src --docs https://github.com/unclecode/doc2talk/tree/main/docs

# Exclude specific patterns
doc2talk --exclude "*/tests/*" --exclude "*/node_modules/*"

# Session management
doc2talk --list                     # List all chat sessions
doc2talk --continue SESSION_ID      # Continue existing session
doc2talk --delete SESSION_ID        # Delete a session
```

### Python API

```python
from doc2talk import Doc2Talk

# Create instance with sources (required)
doc2talk = Doc2Talk(
    code_source="https://github.com/unclecode/doc2talk/tree/main/src",
    docs_source="https://github.com/unclecode/doc2talk/tree/main/docs",
    exclude_patterns=["*/tests/*"]
)

# Lazy loading (faster initialization)
doc2talk = Doc2Talk(code_source="/path/to/code")
# Build index only when needed (chat operations automatically build the index)
doc2talk.build_index()  # Or explicitly build index before chatting

# Ask questions and get responses
response = doc2talk.chat("How does the crawler work?")
print(response)

# Streaming responses (synchronous)
for chunk in doc2talk.chat_stream("What are the main components?"):
    print(chunk, end="", flush=True)
    
# Streaming responses (asynchronous)
async for chunk in doc2talk.chat_stream_async("How does it work?"):
    print(chunk, end="", flush=True)

# Customize history and context limits
doc2talk = Doc2Talk(
    code_source="/path/to/code",
    max_history=100,  # Keep up to 100 messages (default is 50)
    max_contexts=10   # Keep up to 10 contexts (default is 5)
)

# Custom LLM configurations
from doc2talk.models import LLMConfig

# Configure custom models with specific parameters
doc2talk = Doc2Talk(
    code_source="/path/to/code",
    # Model for context decisions
    decision_llm_config=LLMConfig(
        model="gpt-3.5-turbo",  # Cheaper model for decisions
        temprature=0.2,         # Lower temperature for consistency
        max_tokens=200          # Limit token usage
    ),
    # Model for response generation
    generation_llm_config=LLMConfig(
        model="gpt-4o",         # Better model for responses
        temprature=0.7,         # Higher temperature for creativity
        max_tokens=1000         # Allow longer responses
    )
)

# Session management
print(f"Current session ID: {doc2talk.session_id}")
sessions = Doc2Talk.list_sessions()
Doc2Talk.delete_session("session_id")

# Loading from existing index
doc2talk = Doc2Talk.from_index(
    "/path/to/index.c4ai",
    max_history=75,
    max_contexts=3
)
```

## How It Works

Doc2Talk combines several powerful components:

1. **DocGraph**: A knowledge graph engine that:
   - Indexes Python code (classes, functions) and Markdown docs
   - Uses BM25 search algorithm for accurate retrieval
   - Supports both local paths and GitHub repositories
   - Maintains optimized serialization for fast loading

2. **Contextual Decision Making**: 
   - Uses LLMs to determine when to fetch new context
   - Decides between replacement, addition, or reuse of context
   - Avoids redundant context fetching

3. **Repository Management**:
   - Caches repositories at `~/.doctalk/repos/`
   - Intelligently handles multiple paths from the same repository
   - Auto-cleans old repositories not accessed in 30 days

4. **Index Caching**:
   - Stores indexed knowledge graphs at `~/.doctalk/index/`
   - Uses compressed binary format for 50-70% smaller files
   - Memory-mapped files for efficient partial loading

## Directory Structure

```
~/.doctalk/
├── index/          # Cached knowledge graphs
├── repos/          # Cached GitHub repositories
└── sessions/       # Saved chat sessions
```

## Usage Examples

### Creating a New Chat

Start a new chat session by running the CLI:

```bash
doc2talk --code /path/to/code --docs /path/to/docs
```

The first time you run it, it will:
1. Clone the repository if it's a GitHub URL (or use cached version if available)
2. Build the knowledge graph (or load from cache if available)
3. Present you with an interactive chat interface

### Asking Questions

Simply type your questions in the terminal. Doc2Talk will:
1. Analyze your question
2. Determine if new context is needed
3. Search the knowledge graph for relevant information
4. Generate a response based on the retrieved context

Example questions:
- "How does the crawling functionality work?"
- "Can you explain the BM25 search implementation?"
- "What's the structure of the DocGraph class?"

### Advanced Context Management

Doc2Talk uses three context modes:
- **New**: Completely replaces existing context with fresh search results
- **Additional**: Adds new search results to existing context
- **None**: Uses existing context without searching

The system automatically decides which mode to use based on your questions.

## Advanced Features

### Custom LLM Models

Doc2Talk supports using different models for different tasks:

1. **Context Decisions**: Use a cheaper model to decide when to update context
2. **Response Generation**: Use a more powerful model to generate responses

This allows you to balance cost and quality.

### Lazy Loading

Doc2Talk initializes quickly by using lazy loading:

1. Creating a Doc2Talk instance is nearly instantaneous
2. The knowledge graph is only built when needed
3. You can control when to build the index with `build_index()`

This provides faster startup time for applications.

## Performance Optimization

Doc2Talk is designed for speed and efficiency:
- Cached repositories avoid repeated cloning
- Optimized serialization for 100x faster loading
- Memory-mapped reading for efficient resource usage
- Smart context decisions to minimize redundant searches
- Lazy initialization for faster application startup

## Contributing

Contributions are welcome! Here are some areas for improvement:

- Adding support for more repository types (GitLab, Bitbucket)
- Extending language support beyond Python and Markdown
- Improving the semantic search capabilities
- Enhancing the terminal UI

## License

[MIT License](LICENSE)