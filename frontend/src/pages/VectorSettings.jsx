import { useState, useEffect } from 'preact/hooks';
import { getSettings, updateSettings, testQdrantConnection } from '../services/api';

const VectorSettings = () => {
  const [settings, setSettings] = useState({
    QDRANT_HOST: '',
    QDRANT_PORT: '',
    OPENAI_API_KEY: '',
    COLLECTION_NAME: '',
    QDRANT_STATUS: 'unknown',
    MCP_REPO_PATH: ''
  });
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState(false);
  const [refreshingStatus, setRefreshingStatus] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ message: '', severity: 'info' });
  const [testStatus, setTestStatus] = useState({ message: '', severity: 'info' });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await getSettings();
      setSettings(data);
    } catch (error) {
      setSaveStatus({
        message: `Error fetching settings: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const refreshConnectionStatus = async () => {
    try {
      setRefreshingStatus(true);
      const response = await testQdrantConnection();
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: response.status === 'success' ? 'connected' : 'disconnected'
      }));
    } catch (error) {
      console.error('Error refreshing connection status:', error);
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: 'disconnected'
      }));
    } finally {
      setRefreshingStatus(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      setSaveStatus({ message: '', severity: 'info' });
      
      const configItems = Object.entries(settings)
        .filter(([key]) => key !== 'QDRANT_STATUS') // Exclude status field
        .map(([key, value]) => ({
          key,
          value
        }));
      
      // Log the items being sent
      console.log('Saving settings:', configItems);
      
      const response = await updateSettings(configItems);
      
      setSaveStatus({
        message: response.message || 'Settings saved successfully',
        severity: 'success'
      });

      // Explicitly verify that settings were saved by fetching them again
      const updatedSettings = await getSettings();
      console.log('Retrieved settings after save:', updatedSettings);
      setSettings(prevSettings => ({
        ...updatedSettings,
        QDRANT_STATUS: prevSettings.QDRANT_STATUS // Preserve connection status
      }));

      // After updating settings, refresh connection status
      await refreshConnectionStatus();
    } catch (error) {
      setSaveStatus({
        message: `Error saving settings: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestQdrantConnection = async () => {
    try {
      setTestingConnection(true);
      setTestStatus({ message: '', severity: 'info' });
      
      // Save current values first to ensure we test against the values in the form
      const currentSettings = {
        QDRANT_HOST: settings.QDRANT_HOST,
        QDRANT_PORT: settings.QDRANT_PORT,
        COLLECTION_NAME: settings.COLLECTION_NAME
      };
      
      console.log('Testing connection with:', currentSettings);
      
      // Save current form values first so test uses these values
      const configItems = Object.entries(currentSettings).map(([key, value]) => ({
        key, value
      }));
      
      // Apply settings before testing
      await updateSettings(configItems);
      
      // Now test the connection
      const response = await testQdrantConnection();
      
      setTestStatus({
        message: response.message,
        severity: response.status === 'success' ? 'success' : 'error'
      });

      // Update connection status
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: response.status === 'success' ? 'connected' : 'disconnected'
      }));
    } catch (error) {
      setTestStatus({
        message: `Error testing connection: ${error.message}`,
        severity: 'error'
      });
      
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: 'disconnected'
      }));
    } finally {
      setTestingConnection(false);
    }
  };

  const getConnectionStatusClass = () => {
    switch (settings.QDRANT_STATUS) {
      case 'connected':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'disconnected':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  if (loading && Object.values(settings).every(v => v === '' || v === 'unknown')) {
    return (
      <div class="mt-4 flex justify-center">
        <div class="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div class="max-w-3xl mx-auto mt-4">
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex justify-between items-center mb-4">
          <h1 class="text-2xl font-bold">Vector Database Settings</h1>
          <div class="flex items-center">
            <span class="text-sm text-gray-600 mr-2">Connection Status:</span>
            <span class={`text-xs px-2 py-1 rounded-full ${getConnectionStatusClass()} mr-2 border`}>
              {settings.QDRANT_STATUS === 'connected' ? 'Connected' : 'Disconnected'}
            </span>
            <button 
              class="p-1 text-gray-500 hover:text-gray-700 focus:outline-none rounded-full hover:bg-gray-100"
              onClick={refreshConnectionStatus}
              disabled={refreshingStatus}
              title="Refresh connection status"
            >
              {refreshingStatus ? (
                <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <span class="text-lg">🔄</span>
              )}
            </button>
          </div>
        </div>
        <p class="text-gray-600 mb-4">
          Configure the connection to Qdrant vector database and OpenAI API for semantic search capabilities.
        </p>

        <hr class="my-6 border-gray-200" />

        <form onSubmit={handleSubmit}>
          <h2 class="text-xl font-medium mb-4">MCP Repository Settings</h2>
          <div class="grid gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="mcp-repo-path">
                MCP Repository Path
              </label>
              <input
                id="mcp-repo-path"
                type="text"
                name="MCP_REPO_PATH"
                value={settings.MCP_REPO_PATH || ''}
                onChange={handleInputChange}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="/Users/yourname/Documents/Toolbox"
              />
              <p class="mt-1 text-sm text-gray-500">Directory where MCP repositories will be cloned (defaults to Toolbox directory)</p>
            </div>
          </div>

          <hr class="my-6 border-gray-200" />

          <h2 class="text-xl font-medium mb-4">Qdrant Vector Database</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="qdrant-host">
                Qdrant Host
              </label>
              <input
                id="qdrant-host"
                type="text"
                name="QDRANT_HOST"
                value={settings.QDRANT_HOST || ''}
                onChange={handleInputChange}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="localhost"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="qdrant-port">
                Qdrant Port
              </label>
              <input
                id="qdrant-port"
                type="text"
                name="QDRANT_PORT"
                value={settings.QDRANT_PORT || ''}
                onChange={handleInputChange}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="6333"
              />
            </div>
          </div>

          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700 mb-1" for="collection-name">
              Collection Name
            </label>
            <input
              id="collection-name"
              type="text"
              name="COLLECTION_NAME"
              value={settings.COLLECTION_NAME || ''}
              onChange={handleInputChange}
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="mcp_vector_db"
            />
          </div>

          <hr class="my-6 border-gray-200" />

          <h2 class="text-xl font-medium mb-4">OpenAI API Settings</h2>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1" for="openai-key">
              OpenAI API Key
            </label>
            <input
              id="openai-key"
              type="password"
              name="OPENAI_API_KEY"
              value={settings.OPENAI_API_KEY || ''}
              onChange={handleInputChange}
              class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="sk-..."
            />
            <p class="mt-1 text-sm text-gray-500">Required for semantic search of repositories</p>
          </div>

          {saveStatus.message && (
            <div class={`mt-6 p-4 rounded-md ${saveStatus.severity === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
              {saveStatus.message}
            </div>
          )}

          <div class="mt-6 flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-4">
            <button
              type="submit"
              disabled={loading}
              class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save Settings'}
            </button>
            
            <button
              type="button"
              onClick={handleTestQdrantConnection}
              disabled={testingConnection || !settings.QDRANT_HOST || !settings.QDRANT_PORT}
              class="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
            >
              {testingConnection ? 'Testing...' : 'Test Connection'}
            </button>
          </div>
        </form>

        {testStatus.message && (
          <div class={`mt-4 p-4 rounded-md ${testStatus.severity === 'error' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
            {testStatus.message}
          </div>
        )}
      </div>
    </div>
  );
};

export default VectorSettings; 