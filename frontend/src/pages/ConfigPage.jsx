import { useState, useEffect } from 'react';
import { getYamlConfig, getJsonConfig, downloadConfigFile, generateConfigFile } from '../services/api';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { docco } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import yaml from 'react-syntax-highlighter/dist/esm/languages/hljs/yaml';
import json from 'react-syntax-highlighter/dist/esm/languages/hljs/json';

SyntaxHighlighter.registerLanguage('yaml', yaml);
SyntaxHighlighter.registerLanguage('json', json);

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
      <div className="pb-5 border-b border-nextstep-border sm:flex sm:items-center sm:justify-between">
        <h1 className="text-3xl font-bold leading-tight">Configuration</h1>
        <div className="mt-3 sm:mt-0 sm:ml-4 flex space-x-3">
          <div className="inline-flex shadow-sm rounded-md">
            <button
              type="button"
              onClick={() => setConfigType('yaml')}
              className={`relative inline-flex items-center px-4 py-2 rounded-l-md border border-nextstep-border bg-nextstep-card text-sm font-medium ${
                configType === 'yaml' ? 'text-primary-400 z-10' : 'text-nextstep-text-secondary hover:bg-nextstep-border'
              }`}
            >
              YAML
            </button>
            <button
              type="button"
              onClick={() => setConfigType('json')}
              className={`-ml-px relative inline-flex items-center px-4 py-2 rounded-r-md border border-nextstep-border bg-nextstep-card text-sm font-medium ${
                configType === 'json' ? 'text-primary-400 z-10' : 'text-nextstep-text-secondary hover:bg-nextstep-border'
              }`}
            >
              JSON
            </button>
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="nextstep-card overflow-hidden">
          <div className="px-4 py-5 sm:p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg leading-6 font-medium">
                MCP Servers Configuration
              </h3>
              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={handleCopyToClipboard}
                  className="nextstep-button-secondary inline-flex items-center px-4 py-2 text-sm font-medium"
                >
                  {copied ? 'Copied!' : 'Copy to Clipboard'}
                </button>
                <button
                  type="button"
                  onClick={handleDownload}
                  className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Download
                </button>
              </div>
            </div>

            {loading ? (
              <div className="flex justify-center py-8">
                <div className="w-12 h-12 border-t-2 border-b-2 border-primary-500 rounded-full animate-spin"></div>
              </div>
            ) : (
              <div className="mt-2 border border-nextstep-border rounded-md overflow-hidden">
                <SyntaxHighlighter
                  language={configType}
                  style={{
                    ...docco,
                    'hljs': {
                      display: 'block',
                      overflowX: 'auto',
                      padding: '1em',
                      background: '#242424',
                      color: '#e0e0e0',
                    },
                    'hljs-comment': { color: '#888' },
                    'hljs-keyword': { color: '#6495ed' },
                    'hljs-string': { color: '#87ceeb' },
                    'hljs-number': { color: '#ffa07a' },
                    'hljs-name': { color: '#f08080' },
                  }}
                  customStyle={{ margin: 0, padding: '16px', borderRadius: '0.375rem', background: '#242424' }}
                >
                  {config}
                </SyntaxHighlighter>
              </div>
            )}

            {message && (
              <div className={`mt-4 p-4 rounded-md ${message.includes('Failed') ? 'bg-red-900 bg-opacity-20 border border-red-600 text-red-400' : 'bg-green-900 bg-opacity-20 border border-green-600 text-green-400'}`}>
                {message}
                {filePath && !message.includes('Failed') && (
                  <div className="mt-1 text-sm text-nextstep-text-secondary">{filePath}</div>
                )}
              </div>
            )}

            <div className="mt-5">
              <h4 className="text-sm font-medium text-nextstep-text-secondary">How to use:</h4>
              <div className="mt-2 text-sm text-nextstep-text-muted">
                <p>
                  1. Copy or download the configuration above.
                </p>
                <p className="mt-1">
                  2. Save it to your config file (e.g., <code className="px-1 py-0.5 bg-nextstep-border rounded">~/.config/mcp/config.yaml</code>).
                </p>
                <p className="mt-1">
                  3. Use the MCP client to connect to these servers.
                </p>
              </div>
            </div>

            <div className="mt-5 border-t border-nextstep-border pt-5">
              <button
                type="button"
                onClick={handleGenerateFile}
                disabled={generating}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-600 disabled:opacity-50"
              >
                {generating ? 'Generating...' : 'Generate YAML File on Server'}
              </button>
              <p className="mt-2 text-sm text-nextstep-text-muted">
                This will generate the YAML configuration file on the server for direct use.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 