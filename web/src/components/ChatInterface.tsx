import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { v4 as uuidv4 } from 'uuid';
import { Message } from '../App';

interface ChatInterfaceProps {
  sessionId: string;
  initialMessages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  isRebuilding?: boolean;
  rebuildStatus?: string | null;
}

interface MarkdownComponentsProps {
  copyToClipboard: (text: string) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId,
  initialMessages,
  setMessages,
  isRebuilding = false,
  rebuildStatus = null,
}) => {
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [streamedResponse, setStreamedResponse] = useState('');
  const [contextStatus, setContextStatus] = useState<any>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isCopied, setIsCopied] = useState<Record<string, boolean>>({});

  // Connect WebSocket when sessionId changes
  useEffect(() => {
    connectWebSocket();
    return () => {
      if (socket) {
        socket.close();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  useEffect(() => {
    if (initialMessages && initialMessages.length > 0) {
      setMessages(initialMessages);
    }
  }, [initialMessages, setMessages]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [initialMessages, streamedResponse]);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'chunk':
          setStreamedResponse(prev => prev + data.content);
          break;
        case 'context_status':
          setContextStatus(data.status);
          break;
        case 'status':
          setStatusMessage(data.content);
          break;
        case 'complete':
          // Message is now complete, clear streamed response
          setStreamedResponse('');
          setIsLoading(false);
          setStatusMessage(null);
          // Update messages with the complete response
          setMessages(messages => [
            ...messages,
            { role: 'assistant', content: data.content }
          ]);
          break;
        case 'error':
          setErrorMessage(data.content);
          setIsLoading(false);
          setStatusMessage(null);
          break;
        default:
          console.log('Unhandled message type:', data.type);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setErrorMessage('Connection error. Please try refreshing the page.');
    };

    setSocket(ws);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !socket) return;

    // Add user message to state
    setMessages(messages => [...messages, { role: 'user', content: input }]);
    
    // Send message via WebSocket
    if (socket.readyState === WebSocket.OPEN) {
      const messageId = uuidv4();
      socket.send(JSON.stringify({
        type: 'message',
        id: messageId,
        content: input
      }));
      
      // Clear input and set loading state
      setInput('');
      setIsLoading(true);
      setStreamedResponse('');
      setErrorMessage(null);
    } else {
      setErrorMessage('Connection lost. Please refresh the page.');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const copyToClipboard = (text: string) => {
    const blockId = text.slice(0, 20);
    navigator.clipboard.writeText(text).then(() => {
      setIsCopied({ ...isCopied, [blockId]: true });
      setTimeout(() => {
        setIsCopied(prev => ({ ...prev, [blockId]: false }));
      }, 2000);
    });
  };

  const markdownComponents = (props: MarkdownComponentsProps) => ({
    code({ node, inline, className, children, ...props }: any) {
      const match = /language-(\w+)/.exec(className || '');
      const codeText = String(children).replace(/\n$/, '');
      const language = match ? match[1] : '';
      const blockId = codeText.slice(0, 20);
      
      return !inline ? (
        <div className="relative my-4 rounded-md overflow-hidden bg-[#1e1e1e]">
          <div className="flex justify-between items-center bg-[#1e1e1e] border-b border-[#333] px-4 py-2 text-xs font-mono">
            <span className="text-gray-400">{language || 'code'}</span>
            <button
              onClick={() => props.copyToClipboard(codeText)}
              className="text-gray-400 hover:text-white transition-colors flex items-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              {isCopied[blockId] ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <SyntaxHighlighter
            style={vscDarkPlus}
            language={language}
            PreTag="div"
            customStyle={{ 
              margin: 0, 
              padding: '1rem',
              fontSize: '0.875rem',
              lineHeight: 1.5,
              backgroundColor: '#1e1e1e',
              border: 'none'
            }}
            {...props}
          >
            {codeText}
          </SyntaxHighlighter>
        </div>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }
  });

  return (
    <div className="flex flex-col h-full">
      {/* Rebuilding status message */}
      {isRebuilding && rebuildStatus && (
        <div className={`p-3 m-4 rounded text-center ${rebuildStatus.startsWith('Error:') ? 'bg-red-900/50' : 'bg-blue-900/50'}`}>
          <div className="flex items-center justify-center">
            {!rebuildStatus.startsWith('Error:') && (
              <div className="w-4 h-4 mr-2 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
            )}
            <span>{rebuildStatus}</span>
          </div>
        </div>
      )}
      
      {/* Status message */}
      {statusMessage && !isRebuilding && (
        <div className="bg-blue-900/50 p-3 m-4 rounded text-center">
          <div className="flex items-center justify-center">
            <div className="w-4 h-4 mr-2 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
            <span>{statusMessage}</span>
          </div>
        </div>
      )}
      
      {/* Chat messages */}
      <div className="flex-grow overflow-y-auto p-4">
        {initialMessages.map((message, index) => (
          <div key={index} className={`mb-6 ${message.role === 'user' ? 'pl-6' : ''}`}>
            <div className="font-semibold mb-1 text-sm text-gray-400">
              {message.role === 'user' ? 'You' : 'DocTalk'}
            </div>
            <div className={`rounded-lg p-4 ${message.role === 'user' ? 'bg-gray-700' : 'bg-gray-800'}`}>
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents({ copyToClipboard })}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
            {message.role === 'assistant' && contextStatus && index === initialMessages.length - 1 && (
              <div className="text-xs text-gray-500 mt-1">
                {contextStatus.context_count} contexts, {contextStatus.token_count} tokens, {contextStatus.action}
              </div>
            )}
          </div>
        ))}

        {/* Streaming response */}
        {streamedResponse && (
          <div className="mb-6">
            <div className="font-semibold mb-1 text-sm text-gray-400">DocTalk</div>
            <div className="bg-gray-800 rounded-lg p-4">
              <div className="prose prose-invert prose-sm max-w-none">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents({ copyToClipboard })}
                >
                  {streamedResponse}
                </ReactMarkdown>
              </div>
            </div>
            {contextStatus && (
              <div className="text-xs text-gray-500 mt-1">
                {contextStatus.context_count} contexts, {contextStatus.token_count} tokens, {contextStatus.action}
              </div>
            )}
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && !streamedResponse && (
          <div className="mb-6">
            <div className="font-semibold mb-1 text-sm text-gray-400">DocTalk</div>
            <div className="bg-gray-800 rounded-lg p-3">
              <div className="flex space-x-2">
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce"></div>
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}

        {/* Error message */}
        {errorMessage && (
          <div className="mb-6">
            <div className="bg-red-900 text-white rounded-lg p-3">
              Error: {errorMessage}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-gray-700 p-4">
        <form onSubmit={handleSubmit} className="flex items-start">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isRebuilding ? "Please wait while rebuilding index..." : "Ask about your codebase..."}
            className={`flex-grow bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[40px] max-h-[200px] resize-none ${
              isRebuilding ? 'opacity-50' : ''
            }`}
            disabled={isLoading || isRebuilding}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim() || isRebuilding}
            className={`ml-3 px-4 py-2 rounded-lg ${
              isLoading || !input.trim() || isRebuilding
                ? 'bg-gray-700 text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;