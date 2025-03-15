import React, { useState } from 'react';
import CommandPalette from './CommandPalette';
import { Session } from '../App';

interface SessionManagerProps {
  sessions: Session[];
  onSelect: (sessionId: string) => void;
  onCreate: (sessionData: any) => Promise<string | null>;
  onDelete: (sessionId: string) => Promise<void>;
  onRebuildIndex: (sessionId: string) => Promise<void>;
  onClose: () => void;
  onOpenSettings: () => void;
}

const SessionManager: React.FC<SessionManagerProps> = ({
  sessions,
  onSelect,
  onCreate,
  onDelete,
  onRebuildIndex,
  onClose,
  onOpenSettings,
}) => {
  const [showNewSession, setShowNewSession] = useState(false);
  const [codeSource, setCodeSource] = useState('');
  const [docsSource, setDocsSource] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreateNewSession = async () => {
    if (!codeSource && !docsSource) {
      setError('At least one of code source or docs source must be provided');
      return;
    }

    setIsCreating(true);
    setError(null);

    try {
      const sessionData = {
        code_source: codeSource || null,
        docs_source: docsSource || null,
      };

      await onCreate(sessionData);
    } catch (err) {
      setError('Failed to create session');
      console.error(err);
    } finally {
      setIsCreating(false);
    }
  };

  const getCommands = () => {
    const commands = [
      {
        id: 'new-session',
        title: 'Create New Session',
        icon: '➕',
        action: () => setShowNewSession(true),
      },
      ...sessions.map(session => ({
        id: session.session_id,
        title: `Session: ${session.session_id.substring(0, 16)}... (${session.message_count} messages)`,
        icon: '💬',
        action: () => onSelect(session.session_id),
        // Add actions for each session
        showActions: true,
        // Delete action for the delete icon
        deleteAction: () => onDelete(session.session_id),
        // Rebuild action for the rebuild icon
        rebuildAction: async () => {
          try {
            onSelect(session.session_id);
            await onRebuildIndex(session.session_id);
            onClose();
          } catch (err) {
            // Error handling will be done in the parent component
            onClose();
          }
        }
      })),
    ];

    if (sessions.length > 0) {
      commands.push({
        id: 'settings',
        title: 'Open Settings',
        icon: '⚙️',
        action: onOpenSettings,
      });
    }

    return commands;
  };

  if (showNewSession) {
    return (
      <div
        className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center pt-[10vh] z-50"
        onClick={() => setShowNewSession(false)}
      >
        <div
          className="bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl overflow-hidden"
          onClick={e => e.stopPropagation()}
        >
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-xl font-bold">Create New Session</h2>
          </div>

          <div className="p-4">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Code Source (local path or GitHub URL)
              </label>
              <input
                type="text"
                value={codeSource}
                onChange={e => setCodeSource(e.target.value)}
                placeholder="/path/to/code or https://github.com/user/repo/tree/main/src"
                className="w-full bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Docs Source (local path or GitHub URL)
              </label>
              <input
                type="text"
                value={docsSource}
                onChange={e => setDocsSource(e.target.value)}
                placeholder="/path/to/docs or https://github.com/user/repo/tree/main/docs"
                className="w-full bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            {error && (
              <div className="mb-4 bg-red-900 text-white p-3 rounded">
                {error}
              </div>
            )}

            <div className="flex justify-end space-x-2">
              <button
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                onClick={() => setShowNewSession(false)}
              >
                Cancel
              </button>
              <button
                className={`px-4 py-2 bg-blue-600 rounded ${
                  isCreating ? 'opacity-50 cursor-not-allowed' : 'hover:bg-blue-700'
                }`}
                onClick={handleCreateNewSession}
                disabled={isCreating}
              >
                {isCreating ? 'Creating...' : 'Create Session'}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return <CommandPalette commands={getCommands()} onClose={onClose} />;
};

export default SessionManager;