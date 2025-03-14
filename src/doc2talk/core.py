"""
DocTalk Core - Context-aware code documentation chat functionality
"""

import hashlib
import json
import time
import uuid
import warnings
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

from litellm import acompletion

from .docgraph import DocGraph

# Suppress warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# --- Constants ---
HOME_DIR = Path.home() / ".doctalk"
SESSION_DIR = HOME_DIR / "sessions"
DEFAULT_MAX_HISTORY = 50  # Default number of messages to keep
DEFAULT_MAX_CONTEXTS = 5  # Default number of contexts to keep


# --- Core Classes ---
class ChatSession:
    def __init__(self, 
                 session_id: Optional[str] = None,
                 max_history: int = DEFAULT_MAX_HISTORY,
                 max_contexts: int = DEFAULT_MAX_CONTEXTS):
        """
        Initialize a chat session.
        
        Args:
            session_id: Optional session ID to use
            max_history: Maximum number of messages to keep in history
            max_contexts: Maximum number of contexts to keep
        """
        self.session_id = (
            session_id or f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:4]}"
        )
        self.messages: List[Dict] = []
        self.is_new = session_id is None
        self.max_history = max_history
        self.context_manager = ContextManager(max_contexts=max_contexts)

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.messages = self.messages[-self.max_history:]


class SessionManager:
    @staticmethod
    def save(session: ChatSession):
        SESSION_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSION_DIR / f"{session.session_id}.json"
        with open(path, "w") as f:
            json.dump(
                {
                    "id": session.session_id,
                    "messages": session.messages,
                    "contexts": session.context_manager.context_history,
                    "created": datetime.now().isoformat(),
                },
                f,
            )

    @staticmethod
    def load(session_id: str, max_history: int = DEFAULT_MAX_HISTORY, 
             max_contexts: int = DEFAULT_MAX_CONTEXTS) -> ChatSession:
        """
        Load a session from disk.
        
        Args:
            session_id: The ID of the session to load
            max_history: Maximum number of messages to keep in history
            max_contexts: Maximum number of contexts to keep
            
        Returns:
            The loaded ChatSession
        """
        path = SESSION_DIR / f"{session_id}.json"
        with open(path) as f:
            data = json.load(f)
            session = ChatSession(
                data["id"], 
                max_history=max_history,
                max_contexts=max_contexts
            )
            session.messages = data["messages"]
            session.context_manager.context_history = data.get("contexts", [])
            session.is_new = False  # Explicitly mark as not new
            return session

    @staticmethod
    def list_sessions() -> List[Dict]:
        if not SESSION_DIR.exists():
            return []

        sessions = []
        for f in SESSION_DIR.glob("*.json"):
            try:
                with open(f) as file:
                    data = json.load(file)
                    sessions.append(
                        {
                            "id": data["id"],
                            "created": data.get("created", ""),
                            "message_count": len(data["messages"]),
                        }
                    )
            except:  # noqa: E722
                continue

        return sessions

    @staticmethod
    def delete_session(session_id: str) -> bool:
        path = SESSION_DIR / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False


class ContextManager:
    def __init__(self, max_contexts: int = 5):
        self.context_history = []
        self.last_action = "none"
        self.max_contexts = max_contexts  # Number of contexts to keep

    def update(self, new_context: str, mode: str):
        """Update context based on mode (replace|append)"""
        self.last_action = mode
        if mode == "replace":
            self.context_history = [new_context]
        elif mode == "append":
            self.context_history.append(new_context)
            self.context_history = self.context_history[-self.max_contexts :]

    def current_context(self):
        return "\n\n".join(self.context_history)

    def current_token_count(self) -> int:
        return int(len(self.current_context().split()) * 1.5)

    def get_status(self) -> Dict:
        action_map = {
            "replace": "New Context",
            "append": "Additional Context",
            "none": "No Context Added",
        }
        return {
            "context_count": len(self.context_history),
            "token_count": self.current_token_count(),
            "action": action_map[self.last_action],
        }


class ContextDecider:
    def __init__(self, llm_config=None):
        self.llm_config = llm_config
        self.decision_prompt = """Your task is to classify whether we need extra context and knowledge based on a user's question in a chat session with an AI agent. The goal is to optimize and avoid continuously adding new context. Therefore, be very precise in determining if we need new context and classify it into a new category. "New" means that the entire current knowledge context should replace the existing one. However, in many situations, we need both the previous context and the additional one, so you should classify them as "in addition." If there is no need for context related to time, questions, or follow-up questions, classify them as "no context." The goal is to minimize the need for new context. Only when user questions require knowledge referencing back to the Rolfe Rai library should we consider it necessary. Wrap your JSON response in <response> tags.

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

Respond ONLY with <response>{{"decision":"new|additional|none"}}</response>"""  # noqa: E501

    async def decide(self, session: ChatSession, new_question: str):
        try:
            # Prepare the message
            messages = [
                {
                    "role": "system",
                    "content": self.decision_prompt.format(
                        contexts=session.context_manager.current_context(),
                        last_question=session.messages[-2]["content"]
                        if len(session.messages) >= 2
                        else "",
                        new_question=new_question,
                    ),
                }
            ]
            
            # Start with basic parameters
            params = {"messages": messages}
            
            # Add LLM config parameters if available
            if self.llm_config:
                # Use unpacking operator to include all parameters from config
                config_dict = self.llm_config.to_dict()
                # Remove None values
                config_dict = {k: v for k, v in config_dict.items() if v is not None}
                params.update(config_dict)
            else:
                # Default model if no config provided
                params["model"] = "gpt-4o"
            
            # Make the API call
            response = await acompletion(**params)

            # Extract JSON from response
            raw = response.choices[0].message.content
            json_str = raw.split("<response>")[1].split("</response>")[0]
            decision = json.loads(json_str)["decision"]
            return decision

        except Exception as e:
            print(f"Context decision error: {e}")
            return "new"  # Fallback to new context


class ChatEngine:
    def __init__(
        self, code_source=None, docs_source=None, exclude_patterns=None, 
        cache_id=None, force_rebuild=False, max_history=DEFAULT_MAX_HISTORY,
        max_contexts=DEFAULT_MAX_CONTEXTS, 
        decision_llm_config=None, generation_llm_config=None
    ):
        # Centralized cache storage
        self.CACHE_DIR = Path.home() / ".doctalk" / "index"
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Default sources if not provided
        self.code_source = code_source
        self.docs_source = docs_source
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

        if cache_path.exists() and not force_rebuild:
            print(f"Loading knowledge graph from cache ({cache_path.name})...")
            start_time = time.process_time()
            self.knowledge_assistant = DocGraph.load(cache_path)
            load_time = time.process_time() - start_time
            print(f"Knowledge graph loaded in {load_time:.2f}s")
        else:
            print(
                f"Building knowledge graph for:\n- Code: {self.code_source}\n- Docs: {self.docs_source}"  # noqa: E501
            )
            start_time = time.process_time()
            self.knowledge_assistant = DocGraph(
                self.code_source, self.docs_source, self.exclude_patterns
            )
            build_time = time.process_time() - start_time
            print(f"Knowledge graph built in {build_time:.2f}s")

            # Save for future use
            print("Saving knowledge graph to cache...")
            self.knowledge_assistant.persist(cache_path)
            print(f"Knowledge graph cached at {cache_path}")

        # Store LLM configs
        self.decision_llm_config = decision_llm_config
        self.generation_llm_config = generation_llm_config
        
        # Initialize context decider with decision LLM config
        self.decider = ContextDecider(llm_config=decision_llm_config)

    async def get_context_decision(self, session: ChatSession, question: str) -> str:
        """Get context update decision for a question"""
        return await self.decider.decide(session, question)

    async def update_context(
        self, session: ChatSession, question: str, decision: str
    ) -> None:
        """Update session context based on decision"""
        if decision != "none":
            new_context = self.knowledge_assistant.query(question)
            session.context_manager.update(
                new_context, mode="replace" if decision == "new" else "append"
            )

    async def generate_response_stream(
        self, session: ChatSession, question: str
    ) -> AsyncGenerator[str, None]:
        """Generate context-aware response with streaming via yield"""
        try:
            # Get fresh context for each question
            decision = await self.decider.decide(session, question)
            await self.update_context(session, question, decision)

            system_msg = f"""You are DocTalk, an AI assistant for code documentation and explanation.
Answer development questions about the codebase based on the provided context.
Ensure your answers are precise and relevant to the question, using the attached context for guidance,
and avoid hallucinating or fabricating information.

Use this context:
<context>
{session.context_manager.current_context()}
</context>

Answer in markdown."""  # noqa: E501

            # Prepare the messages
            messages = [{"role": "system", "content": system_msg}] + session.messages[-6:]  # Keep last 3 exchanges
            
            # Start with basic parameters
            params = {"messages": messages, "stream": True}
            
            # Add LLM config parameters if available
            if self.generation_llm_config:
                # Use unpacking operator to include all parameters from config
                config_dict = self.generation_llm_config.to_dict()
                # Remove None values
                config_dict = {k: v for k, v in config_dict.items() if v is not None}
                params.update(config_dict)
            else:
                # Default model if no config provided
                params["model"] = "gpt-4o-mini"
            
            # Make the API call
            response = await acompletion(**params)

            # Yield streaming response chunks
            async for chunk in response:
                content = chunk.choices[0].delta.content or ""
                if content:
                    yield content

        except Exception as e:
            yield f"AI Error: {str(e)}"

    async def respond(self, session: ChatSession, question: str) -> str:
        """Generate full response (non-streaming)"""
        try:
            # Get fresh context for each question
            decision = await self.decider.decide(session, question)
            await self.update_context(session, question, decision)

            system_msg = f"""You are DocTalk, an AI assistant for code documentation and explanation.
Answer development questions about the codebase based on the provided context.
Ensure your answers are precise and relevant to the question, using the attached context for guidance,
and avoid hallucinating or fabricating information.

Use this context:
<context>
{session.context_manager.current_context()}
</context>

Answer in markdown."""  # noqa: E501

            # Prepare the messages
            messages = [{"role": "system", "content": system_msg}] + session.messages[-6:]  # Keep last 3 exchanges
            
            # Start with basic parameters
            params = {"messages": messages, "stream": False}
            
            # Add LLM config parameters if available
            if self.generation_llm_config:
                # Use unpacking operator to include all parameters from config
                config_dict = self.generation_llm_config.to_dict()
                # Remove None values
                config_dict = {k: v for k, v in config_dict.items() if v is not None}
                params.update(config_dict)
            else:
                # Default model if no config provided
                params["model"] = "gpt-4o-mini"
            
            # Make the API call
            response = await acompletion(**params)

            return response.choices[0].message.content

        except Exception as e:
            return f"AI Error: {str(e)}"
