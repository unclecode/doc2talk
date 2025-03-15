import React, { useState } from 'react';
import { Editor } from '@monaco-editor/react';
import { Settings } from '../App';

interface SettingsEditorProps {
  settings: Settings;
  onSave: (settings: Settings) => Promise<void>;
  onClose: () => void;
}

const SettingsEditor: React.FC<SettingsEditorProps> = ({
  settings,
  onSave,
  onClose,
}) => {
  const [jsonValue, setJsonValue] = useState<string>(
    JSON.stringify(settings, null, 2)
  );
  const [isValid, setIsValid] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEditorChange = (value: string | undefined) => {
    if (!value) return;
    
    setJsonValue(value);
    
    try {
      JSON.parse(value);
      setIsValid(true);
      setError(null);
    } catch (e) {
      setIsValid(false);
      setError('Invalid JSON: ' + (e as Error).message);
    }
  };

  const handleSave = async () => {
    if (!isValid) return;
    
    try {
      setIsSaving(true);
      setError(null);
      
      const parsedSettings = JSON.parse(jsonValue);
      
      // Validate required fields
      if (!parsedSettings.decision_model || !parsedSettings.generation_model) {
        setError('Both decision_model and generation_model are required');
        setIsSaving(false);
        return;
      }
      
      await onSave(parsedSettings);
    } catch (e) {
      setError('Failed to save settings: ' + (e as Error).message);
    } finally {
      setIsSaving(false);
    }
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
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h2 className="text-xl font-bold">Settings</h2>
          <div className="text-xs bg-blue-600 px-2 py-1 rounded">JSON</div>
        </div>

        <div className="border-b border-gray-700">
          <div className="h-[60vh]">
            <Editor
              defaultLanguage="json"
              value={jsonValue}
              onChange={handleEditorChange}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                lineNumbers: 'on',
                wordWrap: 'on',
              }}
            />
          </div>
        </div>

        {error && (
          <div className="p-3 bg-red-900 text-white">
            {error}
          </div>
        )}

        <div className="p-4 flex justify-end space-x-2">
          <button
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className={`px-4 py-2 rounded ${
              !isValid || isSaving
                ? 'bg-gray-600 opacity-50 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700'
            }`}
            onClick={handleSave}
            disabled={!isValid || isSaving}
          >
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SettingsEditor;