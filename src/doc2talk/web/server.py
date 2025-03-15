"""
Web server for the Doc2Talk web interface
"""

import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..doc2talk import Doc2Talk
from ..models import LLMConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Doc2Talk Web API", description="Web API for Doc2Talk")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active Doc2Talk instances for each session
active_sessions: Dict[str, Doc2Talk] = {}


# -- Pydantic Models --
class SessionCreateRequest(BaseModel):
    code_source: Optional[str] = None
    docs_source: Optional[str] = None
    exclude_patterns: Optional[List[str]] = None
    cache_id: Optional[str] = None
    force_rebuild: bool = False
    max_history: int = 50
    max_contexts: int = 5
    llm_settings: Optional[Dict] = None


class SessionResponse(BaseModel):
    session_id: str
    message_count: int
    created: str


class MessageRequest(BaseModel):
    message: str


class MessageResponse(BaseModel):
    message: str
    role: str


class SessionSettings(BaseModel):
    decision_model: str = "gpt-4o"
    generation_model: str = "gpt-4o-mini"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    exclude_patterns: Optional[List[str]] = None


# -- API Routes --
@app.get("/api/sessions", response_model=List[SessionResponse])
async def list_sessions():
    """List all available sessions"""
    try:
        sessions = Doc2Talk.list_sessions()
        # Convert 'id' field to 'session_id'
        for session in sessions:
            session["session_id"] = session.pop("id")
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(request: SessionCreateRequest):
    """Create a new chat session"""
    try:
        # Configure LLM settings if provided
        decision_llm_config = None
        generation_llm_config = None
        
        if request.llm_settings:
            # Extract LLM settings
            decision_model = request.llm_settings.get("decision_model", "gpt-4o")
            generation_model = request.llm_settings.get("generation_model", "gpt-4o-mini")
            temperature = request.llm_settings.get("temperature")
            max_tokens = request.llm_settings.get("max_tokens")
            
            # Create LLMConfig objects
            decision_llm_config = LLMConfig(
                model=decision_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            generation_llm_config = LLMConfig(
                model=generation_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        # Create Doc2Talk instance
        doc2talk = Doc2Talk(
            code_source=request.code_source,
            docs_source=request.docs_source,
            exclude_patterns=request.exclude_patterns,
            cache_id=request.cache_id,
            force_rebuild=request.force_rebuild,
            max_history=request.max_history,
            max_contexts=request.max_contexts,
            decision_llm_config=decision_llm_config,
            generation_llm_config=generation_llm_config,
        )
        
        # Store the session
        active_sessions[doc2talk.session_id] = doc2talk
        
        # Return session info
        return {
            "session_id": doc2talk.session_id,
            "message_count": 0,
            "created": "now"  # A placeholder, the actual timestamp is set in SessionManager.save
        }
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}", response_model=Dict)
async def get_session(session_id: str):
    """Get session details including messages"""
    try:
        # Check if session is active, if not load it
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = Doc2Talk(session_id=session_id)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
        
        # Get the session
        doc2talk = active_sessions[session_id]
        
        # Return session details
        return {
            "session_id": doc2talk.session_id,
            "messages": doc2talk.messages,
        }
        
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}", response_model=Dict)
async def delete_session(session_id: str):
    """Delete a session"""
    try:
        # Remove from active sessions
        if session_id in active_sessions:
            del active_sessions[session_id]
        
        # Delete the session file
        success = Doc2Talk.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"success": True, "message": f"Session {session_id} deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/messages", response_model=MessageResponse)
async def create_message(session_id: str, request: MessageRequest):
    """Send a message and get a non-streaming response"""
    try:
        # Check if session is active, if not load it
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = Doc2Talk(session_id=session_id)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
        
        # Get the session
        doc2talk = active_sessions[session_id]
        
        # Send message and get response
        response = doc2talk.chat(request.message)
        
        return {"message": response, "role": "assistant"}
        
    except Exception as e:
        logger.error(f"Error creating message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}/settings", response_model=SessionSettings)
async def get_settings(session_id: str):
    """Get session settings"""
    try:
        # Check if session is active, if not load it
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = Doc2Talk(session_id=session_id)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
        
        # Get the session
        doc2talk = active_sessions[session_id]
        
        # Get decision and generation models
        decision_model = "gpt-4o"
        generation_model = "gpt-4o-mini"
        temperature = None
        max_tokens = None
        exclude_patterns = doc2talk._engine_params.get("exclude_patterns", [])
        
        if doc2talk.engine:
            if doc2talk.engine.decision_llm_config:
                decision_model = doc2talk.engine.decision_llm_config.model
                temperature = doc2talk.engine.decision_llm_config.temperature
                max_tokens = doc2talk.engine.decision_llm_config.max_tokens
                
            if doc2talk.engine.generation_llm_config:
                generation_model = doc2talk.engine.generation_llm_config.model
                if not temperature:
                    temperature = doc2talk.engine.generation_llm_config.temperature
                if not max_tokens:
                    max_tokens = doc2talk.engine.generation_llm_config.max_tokens
        
        return {
            "decision_model": decision_model,
            "generation_model": generation_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "exclude_patterns": exclude_patterns
        }
        
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sessions/{session_id}/settings", response_model=Dict)
async def update_settings(session_id: str, settings: SessionSettings):
    """Update session settings"""
    try:
        # Check if session is active, if not load it
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = Doc2Talk(session_id=session_id)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
        
        # Get the session
        doc2talk = active_sessions[session_id]
        
        # Ensure engine is initialized
        doc2talk._ensure_engine_initialized()
        
        # Update LLM configs
        doc2talk.engine.decision_llm_config = LLMConfig(
            model=settings.decision_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        
        doc2talk.engine.generation_llm_config = LLMConfig(
            model=settings.generation_model,
            temperature=settings.temperature,
            max_tokens=settings.max_tokens
        )
        
        # Update exclude patterns if provided
        if settings.exclude_patterns is not None:
            doc2talk._engine_params["exclude_patterns"] = settings.exclude_patterns
        
        return {"success": True, "message": "Settings updated"}
        
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/rebuild", response_model=Dict)
async def rebuild_index(session_id: str):
    """Rebuild the knowledge graph index for a session"""
    try:
        # Check if session is active, if not load it
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = Doc2Talk(session_id=session_id)
            except Exception as e:
                raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")
        
        # Get the session
        doc2talk = active_sessions[session_id]
        
        # Store current sources
        code_source = doc2talk._engine_params.get("code_source")
        docs_source = doc2talk._engine_params.get("docs_source")
        exclude_patterns = doc2talk._engine_params.get("exclude_patterns")
        
        # Check if sources are available
        if not code_source and not docs_source:
            # This is an existing session without source information
            # We cannot rebuild without sources
            raise HTTPException(
                status_code=400, 
                detail="Cannot rebuild index: No source information available. This session may have been created with an older version or loaded from a saved session without source info."
            )
        
        # Force rebuild by resetting engine and rebuilding
        doc2talk.engine = None
        
        # Build with force_rebuild=True
        doc2talk._engine_params["force_rebuild"] = True
        doc2talk._ensure_engine_initialized()
        
        return {
            "success": True, 
            "message": "Knowledge graph rebuilt successfully",
            "sources": {
                "code": code_source,
                "docs": docs_source,
                "exclude_patterns": exclude_patterns
            }
        }
        
    except HTTPException:
        # Pass through HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error rebuilding index: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# -- WebSocket for Streaming Responses --
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
    
    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    try:
        # Check if session exists or load it
        if session_id not in active_sessions:
            try:
                active_sessions[session_id] = Doc2Talk(session_id=session_id)
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "content": f"Session not found: {str(e)}"
                })
                await websocket.close()
                return
        
        # Get session
        doc2talk = active_sessions[session_id]
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "message":
                user_message = message_data.get("content", "")
                
                # Add user message to session
                doc2talk.session.add_message("user", user_message)
                
                # Send acknowledgment
                await websocket.send_json({
                    "type": "message_received",
                    "message_id": message_data.get("id")
                })
                
                # Send streaming response
                full_response = []
                
                # Initialize knowledge graph with status updates
                try:
                    # Send status message about initialization
                    if not doc2talk.engine:
                        await websocket.send_json({
                            "type": "status",
                            "content": "Initializing knowledge graph..."
                        })
                    
                    # Initialize the engine
                    doc2talk._ensure_engine_initialized()
                    
                    # Notify when ready
                    if doc2talk.engine:
                        await websocket.send_json({
                            "type": "status",
                            "content": "Knowledge graph ready"
                        })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Error initializing knowledge graph: {str(e)}"
                    })
                    continue
                
                # First, make a decision about context
                await websocket.send_json({
                    "type": "status",
                    "content": "Analyzing question..."
                })
                decision = await doc2talk.engine.get_context_decision(doc2talk.session, user_message)
                
                if decision != "none":
                    await websocket.send_json({
                        "type": "status",
                        "content": f"Retrieving {decision} context..."
                    })
                
                await doc2talk.engine.update_context(doc2talk.session, user_message, decision)
                
                # Send context status
                context_status = doc2talk.session.context_manager.get_status()
                await websocket.send_json({
                    "type": "context_status",
                    "status": context_status
                })
                
                # Clear status message before generating response
                await websocket.send_json({
                    "type": "status",
                    "content": None
                })
                
                # Then stream the response
                try:
                    async for chunk in doc2talk.engine.generate_response_stream(doc2talk.session, user_message):
                        full_response.append(chunk)
                        await websocket.send_json({
                            "type": "chunk",
                            "content": chunk
                        })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Error generating response: {str(e)}"
                    })
                
                # Add the complete message to the session
                complete_response = "".join(full_response)
                doc2talk.session.add_message("assistant", complete_response)
                
                # Save the session
                try:
                    from ..core import SessionManager
                    SessionManager.save(doc2talk.session)
                    await websocket.send_json({
                        "type": "complete",
                        "content": complete_response
                    })
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "content": f"Error saving session: {str(e)}"
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if session_id in manager.active_connections:
            await websocket.send_json({
                "type": "error",
                "content": f"Server error: {str(e)}"
            })
            manager.disconnect(session_id)


# Note: Static files are now mounted conditionally in the run_server function
# to support development mode


def run_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False, dev_mode: bool = False):
    """Run the web server"""
    # In dev mode, we only want to mount the API, not the static files
    # This allows the React dev server to handle frontend requests
    if dev_mode:
        # Don't mount static files in dev mode
        # The React dev server will handle frontend requests
        pass
    else:
        # Mount static files in production mode
        web_dir = Path(__file__).parent / "dist"
        if web_dir.exists():
            app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="static")
    
    # Run the server with appropriate options
    uvicorn.run("doc2talk.web.server:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    run_server(reload=True)