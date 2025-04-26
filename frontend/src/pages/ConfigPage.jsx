import { useState, useEffect } from 'preact/hooks';
import { getYamlConfig, getJsonConfig, downloadConfigFile, generateConfigFile } from '../services/api';

export default function ConfigPage() {
  const [configType, setConfigType] = useState('yaml');
  const [config, setConfig] = useState('');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [filePath, setFilePath] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const fetchConfig = async () => {
      setLoading(true);
      try {
        if (configType === 'yaml') {
          const yamlConfig = await getYamlConfig();
          setConfig(yamlConfig);
        } else {
          const jsonConfig = await getJsonConfig();
          setConfig(JSON.stringify(jsonConfig, null, 2));
        }
      } catch (error) {
        console.error(`Error fetching ${configType} config:`, error);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, [configType]);

  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(config).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      (err) => {
        console.error('Could not copy text: ', err);
      }
    );
  };

  const handleDownload = () => {
    downloadConfigFile();
  };

  const handleGenerateFile = async () => {
    try {
      setGenerating(true);
      const result = await generateConfigFile();
      setFilePath(result.file_path);
      setMessage('Configuration file generated successfully!');
      setTimeout(() => {
        setMessage('');
      }, 5000);
    } catch (error) {
      console.error('Error generating config file:', error);
      setMessage('Failed to generate configuration file.');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div>
      <div class="pb-5 border-b border-nextstep-border flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <h1 class="text-3xl font-heading font-bold leading-tight">Configuration</h1>
        <div class="mt-3 sm:mt-0 sm:ml-4 flex space-x-3">
          <div class="inline-flex shadow-sm rounded-lg overflow-hidden">
            <button
              type="button"
              onClick={() => setConfigType('yaml')}
              class={`relative inline-flex items-center px-4 py-2 border-r border-nextstep-border bg-white text-sm font-medium transition-colors duration-200 ${
                configType === 'yaml' ? 'text-primary-600 bg-primary-50' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              YAML
            </button>
            <button
              type="button"
              onClick={() => setConfigType('json')}
              class={`relative inline-flex items-center px-4 py-2 bg-white text-sm font-medium transition-colors duration-200 ${
                configType === 'json' ? 'text-primary-600 bg-primary-50' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              JSON
            </button>
          </div>
        </div>
      </div>

      <div class="mt-6">
        <div class="bg-white shadow-nextstep rounded-lg overflow-hidden">
          <div class="px-6 py-6">
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4">
              <h3 class="text-lg font-heading font-medium text-gray-900 mb-2 sm:mb-0">
                MCP Servers Configuration
              </h3>
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleCopyToClipboard}
                  class="inline-flex items-center px-4 py-2 border border-nextstep-border rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors duration-200"
                >
                  {copied ? (
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M7 9a2 2 0 012-2h6a2 2 0 012 2v6a2 2 0 01-2 2H9a2 2 0 01-2-2V9z" />
                      <path d="M5 3a2 2 0 00-2 2v6a2 2 0 002 2V5h8a2 2 0 00-2-2H5z" />
                    </svg>
                  )}
                  {copied ? 'Copied!' : 'Copy to Clipboard'}
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors duration-200"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                  </svg>
                  Download
                </button>
              </div>
            </div>

            {loading ? (
              <div class="flex justify-center py-8">
                <div class="w-10 h-10 border-t-2 border-b-2 border-primary-500 rounded-full animate-spin"></div>
              </div>
            ) : (
              <div class="mt-2 border border-nextstep-border rounded-lg overflow-hidden">
                <pre
                  class="block p-4 bg-gray-800 text-gray-200 text-sm overflow-x-auto"
                  style={{ margin: 0, borderRadius: '0.375rem' }}
                >
                  {config}
                </pre>
              </div>
            )}

            {message && (
              <div class={`mt-4 p-4 rounded-md ${message.includes('Failed') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-green-50 border border-green-200 text-green-700'}`}>
                {message}
                {filePath && !message.includes('Failed') && (
                  <div class="mt-1 text-sm text-gray-600">{filePath}</div>
                )}
              </div>
            )}

            <div class="mt-6">
              <h4 class="text-sm font-medium text-gray-600">How to use:</h4>
              <div class="mt-2 text-sm text-gray-600">
                <p class="flex items-center">
                  <span class="flex-shrink-0 w-5 h-5 inline-flex items-center justify-center rounded-full bg-primary-100 text-primary-500 mr-2">1</span>
                  Copy or download the configuration above.
                </p>
                <p class="mt-2 flex items-center">
                  <span class="flex-shrink-0 w-5 h-5 inline-flex items-center justify-center rounded-full bg-primary-100 text-primary-500 mr-2">2</span>
                  Save it to your config file (e.g., <code class="mx-1 px-1.5 py-0.5 bg-gray-100 rounded text-xs font-mono">~/.config/mcp/config.yaml</code>).
                </p>
                <p class="mt-2 flex items-center">
                  <span class="flex-shrink-0 w-5 h-5 inline-flex items-center justify-center rounded-full bg-primary-100 text-primary-500 mr-2">3</span>
                  Use the MCP client to connect to these servers.
                </p>
              </div>
            </div>

            <div class="mt-6 pt-5 border-t border-nextstep-border">
              <button
                type="button"
                onClick={handleGenerateFile}
                disabled={generating}
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:bg-gray-400 disabled:opacity-60 transition-all duration-200"
              >
                {generating ? (
                  <>
                    <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Generating...
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-2" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clip-rule="evenodd" />
                    </svg>
                    Generate YAML File on Server
                  </>
                )}
              </button>
              <p class="mt-2 text-sm text-gray-600">
                This will generate the YAML configuration file on the server for direct use.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 