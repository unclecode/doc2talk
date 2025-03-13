# chat https://chat.deepseek.com/a/chat/s/64fe5cdf-d0da-46f4-83f6-2c8ad8c928f6

"""
Crawl4AI Terminal Chat with Streaming
"""

from docgraph import DocGraph
import argparse
import asyncio
import json
import time
import uuid
import warnings
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import hashlib

from litellm import acompletion
from rich.console import Console


warnings.filterwarnings("ignore", category=RuntimeWarning)

# Disable UserWarning
warnings.filterwarnings("ignore", category=UserWarning)

# Suppress runtime warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# --- Constants ---
HOME_DIR = Path.home() / ".doctalk"
SESSION_DIR = HOME_DIR / "sessions"
MAX_HISTORY = 50

HAIR_SPACE = "\u200A"  # Thinnest
THIN_SPACE = "\u2009"  # A bit thicker
SIX_PER_EM_SPACE = "\u2006"  # Slightly thicker


# --- Core Classes ---
class ChatSession:
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
        self.messages: List[Dict] = []
        self.console = Console()
        self.is_new = session_id is None
        self.context_manager = ContextManager()  # Add this


    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.messages = self.messages[-MAX_HISTORY:]

class SessionManager:
    @staticmethod
    def save(session: ChatSession):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSION_DIR / f"{session.session_id}.json"
        with open(path, "w") as f:
            json.dump({
                "id": session.session_id,
                "messages": session.messages,
                "contexts": session.context_manager.context_history,
                "created": datetime.now().isoformat(),
            }, f)

    @staticmethod
    def load(session_id: str) -> ChatSession:
        path = SESSION_DIR / f"{session_id}.json"
        with open(path) as f:
            data = json.load(f)
            session = ChatSession(data["id"])
            session.messages = data["messages"]
            session.context_manager.context_history = data.get("contexts", [])
            return session

    @staticmethod
    def list_sessions() -> List[str]:
        return [f.stem for f in SESSION_DIR.glob("*.json")] if SESSION_DIR.exists() else []

# --- Add Context Manager Class ---
class ContextManager:
    def __init__(self):
        self.context_history = []
        self.last_action = "none"
        self.max_contexts = 5  # Keep last 5 contexts
        
    def update(self, new_context: str, mode: str):
        """Update context based on mode (replace|append)"""
        self.last_action = mode
        if mode == "replace":
            self.context_history = [new_context]
        elif mode == "append":
            self.context_history.append(new_context)
            self.context_history = self.context_history[-self.max_contexts:]
        else:
            return
            
    def current_context(self):
        return "\n\n".join(self.context_history)

    def current_token_count(self) -> int:
        # return len(self.encoder.encode(self.current_context()))
        return int(len(self.current_context().split()) * 1.5)
    
    def get_status(self) -> str:
        action_map = {
            "replace": "New Context",
            "append": "Additional Context",
            "none": "No Context Added"
        }
        return (
            f"[dim][{len(self.context_history)} Contexts, "
            f"{self.current_token_count():,} tokens, "
            f"{action_map[self.last_action]}][/dim]"
        )

# --- New Decision Function ---
class ContextDecider:
    def __init__(self):
        self.decision_prompt = """ Your task is to classify whether we need extra context and knowledge based on a user's question in a chat session with an AI agent. The goal is to optimize and avoid continuously adding new context. Therefore, be very precise in determining if we need new context and classify it into a new category. "New" means that the entire current knowledge context should replace the existing one. However, in many situations, we need both the previous context and the additional one, so you should classify them as "in addition." If there is no need for context related to time, questions, or follow-up questions, classify them as "no context." The goal is to minimize the need for new context. Only when user questions require knowledge referencing back to the Rolfe Rai library should we consider it necessary. Wrap your JSON response in <response> tags.
        
        Analyze if the new question requires:
- NEW context (if needs completely different info)
- ADDITIONAL context (if needs more details)
- NO context (if answerable with existing context)

Current Contexts:
<context>
{contexts}
</context>

Last Question: {last_question}
New Question: {new_question}

Respond ONLY with <response>{{"decision":"new|additional|none"}}</response>"""

    async def decide(self, session: ChatSession, new_question: str):
        # if not session.context_manager.context_history:
        #     return "new"
            
        try:
            response = await acompletion(
                model="gpt-4o",
                messages=[{
                    "role": "system",
                    "content": self.decision_prompt.format(
                        contexts=session.context_manager.current_context(),
                        last_question=session.messages[-2]["content"] if len(session.messages)>=2 else "",
                        new_question=new_question
                    )
                }]
            )
            
            # Extract JSON from response
            raw = response.choices[0].message.content
            json_str = raw.split("<response>")[1].split("</response>")[0]
            decision = json.loads(json_str)["decision"]
            return decision
            
        except Exception:
            return "new"  # Fallback to new context
         
class ChatEngine:
    def __init__(self, code_source=None, docs_source=None, exclude_patterns=None, cache_id=None):
        # Centralized cache storage
        self.CACHE_DIR = Path.home() / ".doctalk" / "index"
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        
        # Default sources if not provided
        self.code_source = code_source or "https://github.com/unclecode/crawl4ai/tree/main/crawl4ai"
        self.docs_source = docs_source or "https://github.com/unclecode/crawl4ai/tree/main/docs/md_v2"
        self.exclude_patterns = exclude_patterns or []
        
        # Generate cache ID based on sources or use provided ID
        if cache_id:
            repo_id = cache_id
        else:
            # Create a deterministic ID based on the sources
            source_str = f"{self.code_source}_{self.docs_source}"
            repo_hash = hashlib.md5(source_str.encode()).hexdigest()[:10]
            repo_id = f"doctalk_{repo_hash}"
            
        cache_path = self.CACHE_DIR / f"{repo_id}.c4ai"
        
        if cache_path.exists():
            print(f"Loading knowledge graph from cache ({cache_path.name})...")
            start_time = time.process_time()
            self.knowledge_assistant = DocGraph.load(cache_path)
            load_time = time.process_time() - start_time
            print(f"Knowledge graph loaded in {load_time:.2f}s")
        else:
            print(f"Building knowledge graph for:\n- Code: {self.code_source}\n- Docs: {self.docs_source}")
            start_time = time.process_time()
            self.knowledge_assistant = DocGraph(
                self.code_source,
                self.docs_source,
                self.exclude_patterns
            )
            build_time = time.process_time() - start_time
            print(f"Knowledge graph built in {build_time:.2f}s")
            
            # Save for future use
            print("Saving knowledge graph to cache...")
            self.knowledge_assistant.persist(cache_path)
            print(f"Knowledge graph cached at {cache_path}")
        
        self.decider = ContextDecider()
        
    async def respond(self, session: ChatSession, question: str):
        """Generate context-aware response with streaming"""
        try:
            # Get fresh context for each question
            decision = await self.decider.decide(session, question)
            if decision != "none":
                new_context = self.knowledge_assistant.query(question)
                session.context_manager.update(new_context, 
                    mode="replace" if decision == "new" else "append")

            system_msg = f"You are DocTalk, an AI assistant for code documentation and explanation. Answer development questions about the codebase based on the provided context. Ensure your answers are precise and relevant to the question, using the attached context for guidance, and avoid hallucinating or fabricating information. Use this context:\n<context>{session.context_manager.current_context()}\n</context>\n\nAnswer in markdown."
            
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": system_msg
                }] + session.messages[-6:],  # Keep last 3 exchanges
                stream=True
            )
            
            # Create a Live display context
            from rich.live import Live
            from rich.markdown import Markdown

            full_response = []
            with Live(Markdown(""), refresh_per_second=10) as live:
                async for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    full_response.append(content)
                    # Update the live display with latest markdown
                    live.update(Markdown("".join(full_response)))
            
            # After streaming response
            session.console.print(
                session.context_manager.get_status(), 
                style="dim cyan"
            )
                        
            # print("\n")
            return "".join(full_response)
            
        except Exception as e:
            return f"AI Error: {str(e)}"

    async def respond1(self, session: ChatSession, question: str):
        """Generate context-aware response with streaming"""
        try:
            # Get fresh context for each question
            decision = await self.decider.decide(session, question)
            new_context = self.knowledge_assistant.query(question)
            if decision != "none":
                new_context = self.knowledge_assistant.query(question)
                session.context_manager.update(new_context, 
                    mode="replace" if decision == "new" else "append")

            system_msg = f"You are DocTalk, an AI assistant for code documentation and explanation. Answer development questions about the codebase based on the provided context. Ensure your answers are precise and relevant to the question, using the attached context for guidance, and avoid hallucinating or fabricating information. Use this context:\n<context>{session.context_manager.current_context()}\n</context>\n\nAnswer in markdown."
            
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{
                    "role": "system",
                    "content": system_msg
                }] + session.messages[-6:],  # Keep last 3 exchanges
                stream=True
            )
            
            # Stream response with formatting
            full_response = []
            width = session.console.width - 2  # Account for borders
            session.console.print("┌─[cyan]DocTalk[/cyan]" + "─" * (width - 9))
            
            # Buffer for collecting markdown content
            current_line = ""
            
            async for chunk in response:
                content = chunk.choices[0].delta.content or ""
                for char in content:
                    if char == '\n':
                        # Print completed line with border
                        session.console.print("│ " + current_line)
                        current_line = ""
                    else:
                        current_line += char
                
                # Print partial line without newline
                if current_line:
                    session.console.print("│ " + current_line, end="")
                
                full_response.append(content)
            
            # Print any remaining content
            if current_line:
                session.console.print()  # Complete the last line
                
            # Print context status with border
            session.console.print("│")
            session.console.print("│ " + session.context_manager.get_status())
            
            # Print bottom border
            session.console.print("└" + "─" * (width - 1))
            
            return "".join(full_response)
            
        except Exception as e:
            return f"AI Error: {str(e)}"

class ChatCLI:
    def __init__(self):
        self.console = Console()
        # Track terminal width and listen for changes
        self.width = self.console.width
        self.console.set_window_title("DocTalk - Code Chat")
        self.console.show_cursor(False)

    def draw_box(self, title, color="cyan"):
        """Draw a complete box using terminal width"""
        width = self.console.width - 2
        # Use dim style and ╌ (U+256C) for a dimmer line
        self.console.print(f"[dim]╌[/dim] [{color}]{title}[/{color}] [dim]" + "╌" * (width - len(title) - 3) + "[/dim]")
        return width
    
    async def run(self):
        parser = argparse.ArgumentParser(description='DocTalk - Code Documentation Chat Interface')
        # Session management
        parser.add_argument('--continue', '-c', metavar='ID', help='Continue existing session')
        parser.add_argument('--list', '-l', action='store_true', help='List all saved sessions')
        parser.add_argument('--delete', '-d', metavar='ID', help='Delete a specific session')
        
        # Repository configuration
        parser.add_argument('--code', metavar='PATH', 
                          help='Path to code source (local directory or GitHub URL)')
        parser.add_argument('--docs', metavar='PATH', 
                          help='Path to documentation source (local directory or GitHub URL)')
        parser.add_argument('--exclude', metavar='PATTERN', action='append',
                          help='Glob patterns to exclude (can be used multiple times)')
        parser.add_argument('--cache-id', metavar='ID',
                          help='Custom identifier for the cache file')
        
        args = parser.parse_args()

        if args.list:
            # self.console.print("\n".join(SessionManager.list_sessions()))
            from rich.table import Table
            table = Table(show_header=True)
            table.add_column("Session ID")
            table.add_column("Created")
            table.add_column("Messages")
            
            for session_id in SessionManager.list_sessions():
                try:
                    session = SessionManager.load(session_id)
                    created = session_id.split("-")[0]  # Extract date from ID
                    msg_count = len(session.messages)
                    table.add_row(session_id, created, str(msg_count))
                except:
                    continue
            
            self.console.print(table)
            return

        if args.delete:
            (SESSION_DIR / f"{args.delete}.json").unlink(missing_ok=True)
            return

        session = ChatSession(args.__dict__["continue"]) if args.__dict__["continue"] else ChatSession()
        
        # Initialize ChatEngine with command line arguments
        engine = ChatEngine(
            code_source=args.code,
            docs_source=args.docs,
            exclude_patterns=args.exclude,
            cache_id=args.cache_id
        )
        
        if session.is_new:
            greeting = "Hello! I'm DocTalk, your code documentation assistant. How can I help you today?"
            session.add_message("assistant", greeting)
            self.draw_box("DocTalk", "cyan")
            # self.console.print(f"[cyan][Crawl4ai]:[/cyan] {greeting}")            
            self.console.print(f"{greeting}")            
            self.console.print(HAIR_SPACE)

            SessionManager.save(session)

        while True:
            try:
                # self.console.print("─" * (width))
                self.draw_box("You", "yellow")
                self.console.show_cursor()
                user_input = input().strip()
                self.console.show_cursor()

                if not user_input:
                    continue
                if user_input.lower() == "/exit":
                    break
                
                self.console.print(HAIR_SPACE)

                session.add_message("user", user_input)
                
                # Draw AI response box
                self.draw_box("DocTalk")
                
                response = await engine.respond(session, user_input)
                
                session.add_message("assistant", response)
                SessionManager.save(session)

            except KeyboardInterrupt:
                self.console.print("\n[red]Session saved. Use -c to continue later.[/red]")
                break

async def main():
    await ChatCLI().run()

if __name__ == "__main__":
    asyncio.run(main())
    
    
# Hi, may I know how to set api token when I use LLMExtraction strategy?
# Nice, what if I want local model using Ollama?   