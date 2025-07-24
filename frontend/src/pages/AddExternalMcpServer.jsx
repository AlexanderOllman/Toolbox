import { useState, useEffect } from 'preact/hooks';
import { route } from 'preact-router';
import { createRepository, getSettings } from '../services/api'; // Import createRepository and getSettings
import Modal from '../components/Modal'; // Import Modal component

export default function AddExternalMcpServer() {
  const [serverName, setServerName] = useState('');
  const [description, setDescription] = useState(''); // New state for description
  const [transportProtocol, setTransportProtocol] = useState('http'); // Renamed to avoid conflict with transport in payload
  const [urlValue, setUrlValue] = useState(''); // Renamed
  const [timeoutValue, setTimeoutValueState] = useState(300); // Renamed
  const [headersList, setHeadersList] = useState([{ key: '', value: '' }]); // Renamed
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const [openAIKey, setOpenAIKey] = useState(null); // Store OpenAI key from settings
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);

  useEffect(() => {
    const fetchInitialSettings = async () => {
      try {
        const currentSettings = await getSettings();
        setOpenAIKey(currentSettings.OPENAI_API_KEY || ''); // Store the key, default to empty string if not present
      } catch (err) {
        console.error("Failed to fetch settings:", err);
        // Handle error fetching settings if necessary, perhaps set a general error message
        setError("Could not load required settings. Please try again later.");
      }
    };
    fetchInitialSettings();
  }, []);

  const handleHeaderChange = (index, field, value) => {
    const newHeaders = [...headersList];
    newHeaders[index][field] = value;
    setHeadersList(newHeaders);
  };

  const addHeaderField = () => {
    setHeadersList([...headersList, { key: '', value: '' }]);
  };

  const removeHeaderField = (index) => {
    const newHeaders = headersList.filter((_, i) => i !== index);
    setHeadersList(newHeaders);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Check for OpenAI API Key before other validations
    if (!openAIKey) {
      setIsApiKeyModalOpen(true);
      return; // Stop submission if key is missing
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    if (!serverName.trim()) {
        setError('Server Name is required.');
        setLoading(false);
        return;
    }

    if (!description.trim()) {
        setError('Description is required for external MCP servers.');
        setLoading(false);
        return;
    }

    if (transportProtocol !== 'stdio' && !urlValue.trim()) {
        setError('URL is required for the selected transport protocol.');
        setLoading(false);
        return;
    }

    const formattedHeaders = {};
    headersList.forEach(header => {
      if (header.key.trim()) { // Value can be empty
        formattedHeaders[header.key.trim()] = header.value.trim();
      }
    });

    const payload = {
      name: serverName.trim(),
      repo_url: `external://${serverName.trim()}`, // Convention for external configs
      description: description.trim(),
      transport: transportProtocol,
      url: urlValue.trim(),
      is_external_config: true,
      headers: JSON.stringify(formattedHeaders),
      command: '', // Empty command for external configs
      args: [], // Empty args for external configs
      env: {},
      deploy_as_container: false,
      has_dockerfile: false,
      container_args_template: {},
      container_args_user: {},
      deployment_status: 'n/a_external'
    };

    if (transportProtocol === 'sse' && timeoutValue) {
      payload.read_transport_sse_timeout_seconds = parseInt(timeoutValue, 10);
    }

    try {
      const response = await createRepository(payload);
      setSuccess(true);
      // Reset form
      setServerName('');
      setDescription('');
      setTransportProtocol('http');
      setUrlValue('');
      setTimeoutValueState('');
      setHeadersList([]);

      setTimeout(() => {
        route('/repositories');
      }, 1500); // Redirect after 1.5 seconds
    } catch (error) {
      console.error('Error creating external MCP server:', error);
      setError(error.response?.data?.detail || 'Failed to create external MCP server.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="container">
      <div class="pb-5 border-b border-gray-200">
        <h1 class="text-3xl font-bold leading-tight text-gray-900">Connect External MCP Server</h1>
        <p class="mt-1 text-sm text-gray-500">
          Provide the details of your existing MCP server to connect it.
        </p>
      </div>

      <div class="mt-6">
        <form onSubmit={handleSubmit} class="bg-white shadow rounded-lg p-6 space-y-8 divide-y divide-gray-200">
          {success && (
            <div className="mb-4 rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-700">External MCP Server successfully submitted! Redirecting...</p>
                </div>
              </div>
            </div>
          )}
          {error && (
            <div className="mb-4 rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          <div class="pt-8 space-y-6">
            <div>
              <label htmlFor="serverName" class="block text-sm font-medium text-gray-700">
                Server Name <span class="text-red-500">*</span>
              </label>
              <div class="mt-1">
                <input
                  type="text"
                  name="serverName"
                  id="serverName"
                  value={serverName}
                  onChange={(e) => setServerName(e.target.value)}
                  class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="my-custom-server"
                  required
                />
              </div>
              <p class="mt-2 text-sm text-gray-500">A unique name for this server (e.g., 'my_chat_model'). This will be used as the key in the configuration.</p>
            </div>

            <div>
              <label htmlFor="description" class="block text-sm font-medium text-gray-700">
                Description <span class="text-red-500">*</span>
              </label>
              <div class="mt-1">
                <textarea
                  id="description"
                  name="description"
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  placeholder="A brief description of what this MCP server does or connects to."
                  required
                />
              </div>
              <p class="mt-2 text-sm text-gray-500">Provide a short description for this server. This is required.</p>
            </div>

            <div>
              <label htmlFor="transportProtocol" class="block text-sm font-medium text-gray-700">
                Transport Protocol <span class="text-red-500">*</span>
              </label>
              <div class="mt-1">
                <select
                  id="transportProtocol"
                  name="transportProtocol"
                  value={transportProtocol}
                  onChange={(e) => setTransportProtocol(e.target.value)}
                  class="block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                >
                  <option value="stdio">stdio (default, for local commands)</option>
                  <option value="http">http</option>
                  <option value="sse">sse (Server-Sent Events)</option>
                  <option value="streamable_http">streamable_http</option>
                </select>
              </div>
            </div>

            {transportProtocol !== 'stdio' && (
              <div>
                <label htmlFor="urlValue" class="block text-sm font-medium text-gray-700">
                  URL <span class="text-red-500">*</span>
                </label>
                <div class="mt-1">
                  <input
                    type="url" 
                    name="urlValue"
                    id="urlValue"
                    value={urlValue}
                    onChange={(e) => setUrlValue(e.target.value)}
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="http://localhost:8000/mcp"
                    required={transportProtocol !== 'stdio'}
                  />
                </div>
              </div>
            )}

            {transportProtocol === 'sse' && (
              <div>
                <label htmlFor="timeoutValue" class="block text-sm font-medium text-gray-700">
                  SSE Timeout (seconds)
                </label>
                <div class="mt-1">
                  <input
                    type="number"
                    name="timeoutValue"
                    id="timeoutValue"
                    value={timeoutValue}
                    onChange={(e) => setTimeoutValueState(e.target.value)}
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    placeholder="300"
                  />
                </div>
                <p class="mt-2 text-sm text-gray-500">Optional timeout for SSE connections (read_transport_sse_timeout_seconds).</p>
              </div>
            )}

            <div class="space-y-4">
              <h3 class="text-md font-medium text-gray-900">Headers (Optional)</h3>
              {headersList.map((header, index) => (
                <div key={index} class="grid grid-cols-11 gap-2 items-center">
                  <div class="col-span-5">
                    <label htmlFor={`header-key-${index}`} class="sr-only">Header Key</label>
                    <input
                      type="text"
                      id={`header-key-${index}`}
                      value={header.key}
                      onChange={(e) => handleHeaderChange(index, 'key', e.target.value)}
                      placeholder="Authorization"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                  </div>
                  <div class="col-span-5">
                    <label htmlFor={`header-value-${index}`} class="sr-only">Header Value</label>
                    <input
                      type="text"
                      id={`header-value-${index}`}
                      value={header.value}
                      onChange={(e) => handleHeaderChange(index, 'value', e.target.value)}
                      placeholder="Bearer <secret>"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                    />
                  </div>
                  <div class="col-span-1">
                    {headersList.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeHeaderField(index)}
                        class="text-red-600 hover:text-red-800 p-1 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                      >
                        <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                           <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              ))}
              <button
                type="button"
                onClick={addHeaderField}
                class="mt-2 inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Add Header
              </button>
            </div>
          </div>

          <div class="pt-5">
            <div class="flex justify-end">
              <button
                type="button"
                onClick={() => route('/add-repository-options')}
                class="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                class="ml-3 inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {loading ? 'Connecting...' : 'Connect Server'}
              </button>
            </div>
          </div>
        </form>
      </div>

      <Modal 
        isOpen={isApiKeyModalOpen} 
        onClose={() => setIsApiKeyModalOpen(false)} 
        title="OpenAI API Key Required"
      >
        <p>
          An OpenAI API Key is required to properly process and add repositories, including generating necessary data from descriptions.
        </p>
        <p class="mt-2">
          Please configure your OpenAI API Key in the settings.
        </p>
        {/** Modal actions (buttons) */}
        <div class="mt-4 flex justify-end space-x-2">
          <button 
            type="button"
            onClick={() => setIsApiKeyModalOpen(false)} 
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button 
            type="button"
            onClick={() => {
              setIsApiKeyModalOpen(false);
              route('/settings');
            }} 
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Go to Settings
          </button>
        </div>
      </Modal>
    </div>
  );
} 