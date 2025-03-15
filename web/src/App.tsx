import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';
import CommandPalette from './components/CommandPalette';
import SessionManager from './components/SessionManager';
import SettingsEditor from './components/SettingsEditor';

export interface Session {
  session_id: string;
  message_count: number;
  created: string;
}

export interface Message {
  role: string;
  content: string;
}

export interface Settings {
  decision_model: string;
  generation_model: string;
  temperature?: number;
  max_tokens?: number;
  exclude_patterns?: string[];
}

const App: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSession, setCurrentSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [rebuildStatus, setRebuildStatus] = useState<string | null>(null);
  const [settings, setSettings] = useState<Settings>({
    decision_model: 'gpt-4o',
    generation_model: 'gpt-4o-mini',
  });

  // Handle keyboard shortcut for command palette
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check for Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)
      if ((event.metaKey || event.ctrlKey) && event.shiftKey && event.key === 'p') {
        event.preventDefault();
        setShowCommandPalette(true);
      }
      // Escape key to close modals
      if (event.key === 'Escape') {
        setShowCommandPalette(false);
        setShowSettings(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Fetch sessions on component mount and restore active session
  useEffect(() => {
    fetchSessions().then(() => {
      // Restore active session from localStorage if available
      const savedSessionId = localStorage.getItem('currentSessionId');
      if (savedSessionId) {
        setCurrentSession(savedSessionId);
      }
    });
  }, []);

  // Fetch messages when current session changes and save to localStorage
  useEffect(() => {
    if (currentSession) {
      // Save current session to localStorage
      localStorage.setItem('currentSessionId', currentSession);
      
      // Fetch messages and settings
      fetchMessages(currentSession);
      fetchSettings(currentSession);
    } else {
      // If no current session, remove from localStorage
      localStorage.removeItem('currentSessionId');
    }
  }, [currentSession]);

  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/sessions');
      const data = await response.json();
      setSessions(data);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    }
  };

  const fetchMessages = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}`);
      
      if (!response.ok) {
        // If session doesn't exist anymore (404), clear it
        if (response.status === 404) {
          console.warn(`Session ${sessionId} not found, it may have been deleted`);
          setCurrentSession(null);
          localStorage.removeItem('currentSessionId');
          return;
        }
        throw new Error(`Error ${response.status}: ${await response.text()}`);
      }
      
      const data = await response.json();
      setMessages(data.messages || []);
    } catch (error) {
      console.error('Error fetching messages:', error);
    }
  };

  const fetchSettings = async (sessionId: string) => {
    try {
      const response = await fetch(`/api/sessions/${sessionId}/settings`);
      
      if (!response.ok) {
        // If session doesn't exist anymore (404), clear it
        if (response.status === 404) {
          console.warn(`Session ${sessionId} not found when fetching settings`);
          // Don't clear session here, fetchMessages already does that
          return;
        }
        throw new Error(`Error ${response.status}: ${await response.text()}`);
      }
      
      const data = await response.json();
      setSettings(data);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const createSession = async (sessionData: any) => {
    try {
      const response = await fetch('/api/sessions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sessionData),
      });
      const data = await response.json();
      setCurrentSession(data.session_id);
      setSessions([...sessions, data]);
      setMessages([]);
      return data.session_id;
    } catch (error) {
      console.error('Error creating session:', error);
      return null;
    }
  };

  const deleteSession = async (sessionId: string) => {
    try {
      await fetch(`/api/sessions/${sessionId}`, {
        method: 'DELETE',
      });
      setSessions(sessions.filter(s => s.session_id !== sessionId));
      
      // If the deleted session is the current one, clear it
      if (currentSession === sessionId) {
        setCurrentSession(null);
        setMessages([]);
        // Remove from localStorage too
        localStorage.removeItem('currentSessionId');
      }
    } catch (error) {
      console.error('Error deleting session:', error);
    }
  };

  const updateSettings = async (newSettings: Settings) => {
    if (!currentSession) return;
    
    try {
      await fetch(`/api/sessions/${currentSession}/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newSettings),
      });
      setSettings(newSettings);
    } catch (error) {
      console.error('Error updating settings:', error);
    }
  };

  const handleSessionSelect = (sessionId: string) => {
    setCurrentSession(sessionId);
    setShowCommandPalette(false);
  };

  const handleCreateSession = async (sessionData: any) => {
    const sessionId = await createSession(sessionData);
    setShowCommandPalette(false);
    return sessionId;
  };

  const handleDeleteSession = async (sessionId: string) => {
    await deleteSession(sessionId);
  };
  
  const handleRebuildIndex = async (sessionId: string) => {
    try {
      // Start rebuilding - set UI state
      setIsRebuilding(true);
      setRebuildStatus('Preparing to rebuild knowledge graph...');
      
      // Make sure this session is selected
      setCurrentSession(sessionId);
      
      // Send rebuild request
      const response = await fetch(`/api/sessions/${sessionId}/rebuild`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error rebuilding index:', errorText);
        
        // Display friendly error
        let errorMessage = "Failed to rebuild index.";
        
        try {
          // Try to parse error detail from JSON response
          const errorData = JSON.parse(errorText);
          if (errorData.detail) {
            errorMessage = errorData.detail;
          }
        } catch (e) {
          // If we can't parse JSON, use generic message
        }
        
        // Show error status
        setRebuildStatus(`Error: ${errorMessage}`);
        setTimeout(() => {
          setIsRebuilding(false);
          setRebuildStatus(null);
        }, 5000); // Clear error after 5 seconds
        
        throw new Error(errorMessage);
      } else {
        // Set success status
        setRebuildStatus('Successfully rebuilt knowledge graph!');
        
        // Refresh messages
        fetchMessages(sessionId);
        
        // Clear rebuilding status after delay
        setTimeout(() => {
          setIsRebuilding(false);
          setRebuildStatus(null);
        }, 3000);
      }
    } catch (error) {
      console.error('Error rebuilding index:', error);
      
      // Ensure we clear rebuilding state even on error
      if (!rebuildStatus?.startsWith('Error:')) {
        setRebuildStatus(`Error: ${error}`);
        setTimeout(() => {
          setIsRebuilding(false);
          setRebuildStatus(null);
        }, 5000);
      }
      
      throw error;
    }
  };

  const openSettings = () => {
    setShowSettings(true);
    setShowCommandPalette(false);
  };

  const saveSettings = async (newSettings: Settings) => {
    await updateSettings(newSettings);
    setShowSettings(false);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 py-2 px-4 flex justify-between items-center border-b border-gray-700">
        <div className="flex items-center">
          <h1 className="text-xl font-bold mr-4">Doc2Talk</h1>
          <span className="text-xs bg-blue-600 px-2 py-1 rounded">Web</span>
        </div>
        <div className="flex items-center space-x-2">
          <button 
            onClick={() => setShowCommandPalette(true)}
            className="bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-sm flex items-center"
          >
            <span className="mr-1">⌘</span>
            <span className="mr-1">⇧</span>
            <span>P</span>
          </button>
          {currentSession && (
            <button 
              onClick={openSettings}
              className="bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-sm"
            >
              Settings
            </button>
          )}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-grow flex flex-col overflow-hidden">
        {currentSession ? (
          <ChatInterface
            sessionId={currentSession}
            initialMessages={messages}
            setMessages={setMessages}
            isRebuilding={isRebuilding}
            rebuildStatus={rebuildStatus}
          />
        ) : (
          <div className="flex-grow flex items-center justify-center text-center">
            <div className="max-w-md mx-auto p-6">
              <h2 className="text-2xl font-bold mb-4">Welcome to Doc2Talk</h2>
              <p className="mb-6">Create a new session or select an existing one to get started.</p>
              <button
                onClick={() => setShowCommandPalette(true)}
                className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
              >
                Create or Select a Session
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Command Palette Modal */}
      {showCommandPalette && (
        <SessionManager
          sessions={sessions}
          onSelect={handleSessionSelect}
          onCreate={handleCreateSession}
          onDelete={handleDeleteSession}
          onRebuildIndex={handleRebuildIndex}
          onClose={() => setShowCommandPalette(false)}
          onOpenSettings={openSettings}
        />
      )}

      {/* Settings Modal */}
      {showSettings && (
        <SettingsEditor
          settings={settings}
          onSave={saveSettings}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
};

export default App;