# Doc2Talk

A fast, context-aware code documentation chat interface that provides intelligent responses based on your codebase and documentation.

## Features

- **Knowledge Graph Indexing**: Indexes both code and documentation for comprehensive understanding
- **Smart Context Management**: Intelligently decides when to fetch new context or use existing context
- **Repository Caching**: Efficiently caches GitHub repositories for faster repeated access
- **High-Performance Storage**: Uses optimized serialization for 100x faster loading times
- **Terminal UI**: Rich terminal interface with interactive streaming responses
- **Session Management**: Save and restore chat sessions for continuous workflows

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/doc2talk.git
cd doc2talk

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Command Line Interface

```bash
# Basic usage with default repository (Crawl4AI)
doc2talk

# Specify custom code and documentation sources
doc2talk --code /path/to/code --docs /path/to/docs

# Use a GitHub repository
doc2talk --code https://github.com/username/repo/tree/main/src --docs https://github.com/username/repo/tree/main/docs

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

# Simple usage with default repository
doc2talk = Doc2Talk()
response = doc2talk.chat("How does the crawler work?")
print(response)

# Custom repositories
doc2talk = Doc2Talk(
    code_source="/path/to/code",
    docs_source="/path/to/docs",
    exclude_patterns=["*/tests/*"]
)

# Streaming response
for chunk in doc2talk.chat_stream("What are the main components?"):
    print(chunk, end="", flush=True)

# Session management
print(f"Current session: {doc2talk.session_id}")
sessions = Doc2Talk.list_sessions()
Doc2Talk.delete_session("session_id")

# Loading from existing index
doc2talk = Doc2Talk.from_index("/path/to/index.c4ai")
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
   - Caches repositories at `~/.doc2talk/repos/`
   - Intelligently handles multiple paths from the same repository
   - Auto-cleans old repositories not accessed in 30 days

4. **Index Caching**:
   - Stores indexed knowledge graphs at `~/.doc2talk/index/`
   - Uses compressed binary format for 50-70% smaller files
   - Memory-mapped files for efficient partial loading

## Directory Structure

```
~/.doc2talk/
├── index/          # Cached knowledge graphs
├── repos/          # Cached GitHub repositories
└── sessions/       # Saved chat sessions
```

## Usage Examples

### Creating a New Chat

Start a new chat session by running the CLI:

```bash
python doc2talk.py
```

The first time you run it, it will:
1. Clone the repository (or use cached version if available)
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

## Configuration

Doc2Talk uses sensible defaults, but you can customize:

- Repository sources: Edit the GitHub URLs in `doc2talk.py`
- Cache expiration: Modify `MAX_REPO_AGE_DAYS` in `docgraph.py`
- Context limits: Adjust `max_contexts` in the `ContextManager` class

## Performance Optimization

Doc2Talk is designed for speed and efficiency:
- Cached repositories avoid repeated cloning
- Optimized serialization for 100x faster loading
- Memory-mapped reading for efficient resource usage
- Smart context decisions to minimize redundant searches

## Contributing

Contributions are welcome! Here are some areas for improvement:

- Adding support for more repository types (GitLab, Bitbucket)
- Extending language support beyond Python and Markdown
- Improving the semantic search capabilities
- Enhancing the terminal UI

## License

[MIT License](LICENSE)