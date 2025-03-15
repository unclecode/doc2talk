import React, { useState, useEffect, useRef } from 'react';

interface Command {
  id: string;
  title: string;
  action: () => void;
  icon?: string;
  showActions?: boolean;
  deleteAction?: () => void;
  rebuildAction?: () => void;
}

interface CommandPaletteProps {
  commands: Command[];
  onClose: () => void;
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ commands, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const [filteredCommands, setFilteredCommands] = useState(commands);

  useEffect(() => {
    // Focus input on mount
    inputRef.current?.focus();
  }, []);

  // Filter commands when search term changes
  useEffect(() => {
    const filtered = commands.filter(command =>
      command.title.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredCommands(filtered);
    setSelectedIndex(0);
  }, [searchTerm, commands]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => (prev + 1) % filteredCommands.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => (prev - 1 + filteredCommands.length) % filteredCommands.length);
        break;
      case 'Enter':
        e.preventDefault();
        if (filteredCommands[selectedIndex]) {
          filteredCommands[selectedIndex].action();
        }
        break;
      case 'Escape':
        e.preventDefault();
        onClose();
        break;
      default:
        break;
    }
  };

  const handleCommandClick = (command: Command) => {
    command.action();
  };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center pt-[10vh] z-50"
      onClick={onClose}
    >
      <div
        className="bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Search input */}
        <div className="p-4 border-b border-gray-700">
          <input
            ref={inputRef}
            type="text"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search commands..."
            className="w-full bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Command list */}
        <div className="overflow-y-auto max-h-[70vh]">
          {filteredCommands.length > 0 ? (
            <div className="py-2">
              {filteredCommands.map((command, index) => (
                <div
                  key={command.id}
                  className={`px-4 py-2 cursor-pointer flex items-center justify-between group ${
                    index === selectedIndex ? 'bg-gray-700' : 'hover:bg-gray-700'
                  }`}
                  onClick={() => handleCommandClick(command)}
                >
                  <div className="flex items-center">
                    {command.icon && (
                      <span className="mr-3 text-gray-400">{command.icon}</span>
                    )}
                    <span>{command.title}</span>
                  </div>
                  
                  {command.showActions && (
                    <div className="flex space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      {command.rebuildAction && (
                        <button
                          className="text-gray-500 hover:text-blue-500"
                          onClick={(e) => {
                            e.stopPropagation();
                            command.rebuildAction!();
                          }}
                          title="Rebuild index"
                        >
                          🔄
                        </button>
                      )}
                      {command.deleteAction && (
                        <button
                          className="text-gray-500 hover:text-red-500"
                          onClick={(e) => {
                            e.stopPropagation();
                            command.deleteAction!();
                          }}
                          title="Delete session"
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-gray-400">
              No commands found matching "{searchTerm}"
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;