import { useState, useEffect } from 'preact/hooks';
import { getSettings, updateSettings, testQdrantConnection, getDockerStatus, getCollectionStatus, initializeCollections } from '../services/api';

const SettingsPage = () => {
  const [settings, setSettings] = useState({
    QDRANT_HOST: '',
    QDRANT_PORT: '',
    OPENAI_API_KEY: '',
    COLLECTION_NAME: '',
    QDRANT_STATUS: 'unknown',
    MCP_REPO_PATH: '',
    CONTAINER_HOST: '',
    CONTAINER_HOST_USERNAME: '',
    CONTAINER_HOST_PASSWORD: ''
  });
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState(false);
  const [refreshingStatus, setRefreshingStatus] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ message: '', severity: 'info' });
  const [testStatus, setTestStatus] = useState({ message: '', severity: 'info' });
  const [dockerStatus, setDockerStatus] = useState({ status: 'checking', message: '' });
  const [collectionStatus, setCollectionStatus] = useState({ status: 'unknown', message: '' });
  const [initializingCollections, setInitializingCollections] = useState(false);
  const [initStatus, setInitStatus] = useState({ message: '', severity: 'info' });

  useEffect(() => {
    fetchSettings();
    fetchDockerStatus();
    fetchCollectionStatus();
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

  const fetchDockerStatus = async () => {
    try {
      setDockerStatus({ status: 'checking', message: '' });
      const statusData = await getDockerStatus();
      setDockerStatus({ 
        status: statusData.status || 'error', 
        message: statusData.message || (statusData.status === 'available' ? (statusData.method ? `Connected via ${statusData.method}` : 'Connected') : 'Unknown error') 
      });
    } catch (error) {
      console.error("Error fetching Docker status:", error);
      setDockerStatus({ 
        status: 'error', 
        message: error.response?.data?.message || error.message || 'Failed to fetch Docker status from server' 
      });
    }
  };

  const fetchCollectionStatus = async () => {
    try {
      setCollectionStatus({ status: 'checking', message: '' });
      const statusData = await getCollectionStatus();
      setCollectionStatus({ 
        status: statusData.status || 'error', 
        message: statusData.message || 'Unknown collection status',
        collection_name: statusData.collection_name,
        vector_count: statusData.vector_count
      });
    } catch (error) {
      console.error("Error fetching collection status:", error);
      setCollectionStatus({ 
        status: 'error', 
        message: error.response?.data?.message || error.message || 'Failed to fetch collection status from server' 
      });
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
      // Also refresh collection status when refreshing connection
      await fetchCollectionStatus();
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

  const handleInitializeCollections = async () => {
    try {
      setInitializingCollections(true);
      setInitStatus({ message: '', severity: 'info' });
      
      const response = await initializeCollections();
      
      if (response.status === 'success') {
        setInitStatus({
          message: response.message,
          severity: 'success'
        });
        // Refresh collection status after successful initialization
        await fetchCollectionStatus();
      } else {
        setInitStatus({
          message: response.message || 'Failed to initialize collections',
          severity: 'error'
        });
      }
    } catch (error) {
      console.error('Error initializing collections:', error);
      setInitStatus({
        message: error.response?.data?.message || error.message || 'Failed to initialize collections',
        severity: 'error'
      });
    } finally {
      setInitializingCollections(false);
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
        .filter(([key, value]) => key !== 'QDRANT_STATUS' && typeof value === 'string') // Exclude status AND ensure value is a string
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

  const getCollectionStatusClass = () => {
    switch (collectionStatus.status) {
      case 'connected':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'missing':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      case 'disconnected':
      case 'error':
        return 'bg-red-100 text-red-800 border-red-300';
      case 'checking':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  const getCollectionStatusText = () => {
    switch (collectionStatus.status) {
      case 'connected':
        return `Connected (${collectionStatus.vector_count || 0} vectors)`;
      case 'missing':
        return 'Missing';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Error';
      case 'checking':
        return 'Checking...';
      default:
        return 'Unknown';
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
          <h1 class="text-2xl font-bold">Settings</h1>
          <div class="flex items-center space-x-4">
            {/* Qdrant Connection Status */}
            <div class="flex items-center">
              <span class="text-sm text-gray-600 mr-2">Qdrant:</span>
              <span class={`text-xs px-2 py-1 rounded-full ${getConnectionStatusClass()} border`}>
                {settings.QDRANT_STATUS === 'connected' ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            
            {/* Collection Status */}
            <div class="flex items-center">
              <span class="text-sm text-gray-600 mr-2">Collections:</span>
              <span class={`text-xs px-2 py-1 rounded-full ${getCollectionStatusClass()} border`}>
                {getCollectionStatusText()}
              </span>
            </div>
            
            {/* Refresh Button */}
            <button 
              class="p-1 text-gray-500 hover:text-gray-700 focus:outline-none rounded-full hover:bg-gray-100"
              onClick={refreshConnectionStatus}
              disabled={refreshingStatus}
              title="Refresh status"
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
          Configure connections to Qdrant, OpenAI, Docker host, and other services.
        </p>

        <hr class="my-6 border-gray-200" />

        <div>
          <div class="flex justify-between items-center mb-2">
            <h2 class="text-xl font-medium">Docker Connectivity</h2>
            <button
              onClick={fetchDockerStatus}
              disabled={dockerStatus.status === 'checking'}
              class="p-1 text-gray-500 hover:text-gray-700 focus:outline-none rounded-full hover:bg-gray-100 disabled:opacity-50"
              title="Refresh Docker status"
            >
              {dockerStatus.status === 'checking' ? (
                <div class="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              ) : (
                <span class="text-lg">🔄</span>
              )}
            </button>
          </div>
          {dockerStatus.status === 'checking' && <p class="text-sm text-gray-500">Checking Docker status...</p>}
          {dockerStatus.status === 'available' && (
            <div class="flex items-center text-sm text-green-600 p-2 bg-green-50 rounded-md">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
              </svg>
              <span><strong>Available:</strong> {dockerStatus.message}</span>
            </div>
          )}
          {dockerStatus.status === 'unavailable' && (
            <div class="flex items-center text-sm text-red-600 p-2 bg-red-50 rounded-md">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
              </svg>
              <span><strong>Unavailable:</strong> {dockerStatus.message}</span>
            </div>
          )}
           {dockerStatus.status === 'misconfigured' && (
            <div class="flex items-center text-sm text-orange-500 p-2 bg-orange-50 rounded-md">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                 <path fill-rule="evenodd" d="M8.257 3.099a.75.75 0 01.928-.53l10.5 6.062a.75.75 0 010 1.298l-10.5 6.062a.75.75 0 01-1.463-.65l1.75-10.104a.75.75 0 01.535-.649l.25-.07zM10 8.25a.75.75 0 01.75.75v3a.75.75 0 01-1.5 0v-3A.75.75 0 0110 8.25zM10 15a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
              </svg>
              <span><strong>Configuration Issue:</strong> {dockerStatus.message}</span>
            </div>
          )}
          {dockerStatus.status === 'error' && (
             <div class="flex items-center text-sm text-red-600 p-2 bg-red-50 rounded-md">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.293-5.707a1 1 0 001.414-1.414L11.414 10l.293-.293a1 1 0 00-1.414-1.414L10 8.586l-1.293-1.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293z" clip-rule="evenodd" />
              </svg>
              <span><strong>Error:</strong> {dockerStatus.message}</span>
            </div>
          )}
        </div>

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

          <h2 class="text-xl font-medium mb-4">Container Host Settings</h2>
          <p class="text-gray-600 mb-4">
            Configure the Docker container host for deploying MCP containers.
            The host IP is typically the IP address of the machine running this application's Docker container.
          </p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="container-host">
                Container Host IP
              </label>
              <input
                id="container-host"
                type="text"
                name="CONTAINER_HOST"
                value={settings.CONTAINER_HOST || ''}
                onChange={handleInputChange}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="host.docker.internal"
              />
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="container-host-username">
                Username (Optional)
              </label>
              <input
                id="container-host-username"
                type="text"
                name="CONTAINER_HOST_USERNAME"
                value={settings.CONTAINER_HOST_USERNAME || ''}
                onChange={handleInputChange}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter username if required"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1" for="container-host-password">
                Password (Optional)
              </label>
              <input
                id="container-host-password"
                type="password"
                name="CONTAINER_HOST_PASSWORD"
                value={settings.CONTAINER_HOST_PASSWORD || ''}
                onChange={handleInputChange}
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter password if required"
              />
            </div>
          </div>

          <hr class="my-6 border-gray-200" />

          <h2 class="text-xl font-medium mb-4">Qdrant Vector Database</h2>
          <p class="text-gray-600 mb-4">
            Configure connection to Qdrant for vector storage and semantic search.
          </p>
          
          {/* Initialize Collections Button */}
          <div class="mb-6 p-4 bg-gray-50 rounded-lg border">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-lg font-medium text-gray-900">Database Collections</h3>
                <p class="text-sm text-gray-600">
                  Initialize the required collections in your Qdrant database.
                </p>
              </div>
              <button
                type="button"
                onClick={handleInitializeCollections}
                disabled={initializingCollections || settings.QDRANT_STATUS !== 'connected' || collectionStatus.status !== 'missing'}
                class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {initializingCollections ? (
                  <div class="flex items-center">
                    <div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                    Initializing...
                  </div>
                ) : (
                  'Initialize Collections'
                )}
              </button>
            </div>
            
            {collectionStatus.status === 'missing' && settings.QDRANT_STATUS === 'connected' && (
              <div class="mt-3 p-3 rounded-md text-sm bg-blue-100 text-blue-700 border border-blue-200">
                Collection '{collectionStatus.collection_name}' not found. Click 'Initialize Collections' to create it.
              </div>
            )}
            
            {initStatus.message && (
              <div class={`mt-3 p-3 rounded-md text-sm ${initStatus.severity === 'error' ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-green-100 text-green-700 border border-green-200'}`}>
                {initStatus.message}
              </div>
            )}
          </div>
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

export default SettingsPage; 