import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRepository, fetchRepositoryDetails } from '../services/api';

export default function AddRepository() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    name: '',
    repo_url: '',
    description: '',
    command: '',
    args: [],
    transport: 'stdio', // Default to stdio
    url: '',
    read_timeout_seconds: '',
    read_transport_sse_timeout_seconds: 300, // Default to 300
    headers: '{}',
    api_key: '',
    env: '{}',
    roots_table: ''
  });
  const [newArg, setNewArg] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [fetchingDetails, setFetchingDetails] = useState(false);
  const [detailsFetched, setDetailsFetched] = useState(false);
  const [success, setSuccess] = useState(false);
  const [addedRepo, setAddedRepo] = useState('');

  // Derive whether to show additional fields based on transport
  const showAdditionalFields = formData.transport !== 'stdio';

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    
    // When user types in the repo URL, reset the detailsFetched flag
    if (name === 'repo_url') {
      setDetailsFetched(false);
    }
  };

  const handleFetchDetails = async () => {
    if (!formData.repo_url || !formData.repo_url.includes('github.com')) {
      setError('Please enter a valid GitHub repository URL');
      return;
    }

    setFetchingDetails(true);
    setError(null);

    try {
      const details = await fetchRepositoryDetails(formData.repo_url);
      
      setFormData((prev) => ({
        ...prev,
        name: details.name || prev.name,
        description: details.description || prev.description,
        command: details.command || prev.command,
        args: details.args || prev.args
      }));
      
      setDetailsFetched(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch repository details. Please try again.');
    } finally {
      setFetchingDetails(false);
    }
  };

  const handleAddArg = () => {
    if (newArg.trim()) {
      setFormData((prev) => ({
        ...prev,
        args: [...prev.args, newArg.trim()],
      }));
      setNewArg('');
    }
  };

  const handleRemoveArg = (index) => {
    setFormData((prev) => ({
      ...prev,
      args: prev.args.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const response = await createRepository(formData);
      setSuccess(true);
      setAddedRepo(response.name || formData.name);
      
      // Navigate after a short delay to show the success message
      setTimeout(() => {
        navigate('/repositories');
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add repository. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="pb-5 border-b border-nextstep-border">
        <h1 className="text-3xl font-bold leading-tight">Add Repository</h1>
      </div>

      <div className="mt-6">
        <div className="nextstep-card p-6">
          {success && (
            <div className="mb-6 rounded-md bg-green-900 bg-opacity-20 p-4 border border-green-600">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-400">
                    Repository "{addedRepo}" successfully added to Qdrant database! Redirecting...
                  </h3>
                </div>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-8 divide-y divide-nextstep-border">
            <div className="space-y-8">
              <div>
                <div>
                  <p className="mt-1 text-sm text-nextstep-text-secondary">
                    Add a Git repository to manage as an MCP server.
                  </p>
                </div>

                <div className="mt-6 grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                  <div className="sm:col-span-6">
                    <label htmlFor="repo_url" className="block text-sm font-medium text-nextstep-text-primary">
                      Repository URL
                    </label>
                    <div className="mt-1 flex">
                      <input
                        type="text"
                        name="repo_url"
                        id="repo_url"
                        value={formData.repo_url}
                        onChange={handleChange}
                        placeholder="https://github.com/username/repo.git"
                        className="nextstep-input flex-grow px-3 py-2"
                        required
                      />
                      <button
                        type="button"
                        onClick={handleFetchDetails}
                        disabled={fetchingDetails || !formData.repo_url}
                        className="ml-3 inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-gray-600 disabled:opacity-50"
                      >
                        {fetchingDetails ? 'Fetching...' : detailsFetched ? 'Refresh Details' : 'Fetch Details'}
                      </button>
                    </div>
                    <p className="mt-2 text-sm text-nextstep-text-muted">
                      The Git URL of the repository to add. Click "Fetch Details" to automatically populate fields.
                    </p>
                  </div>

                  <div className="sm:col-span-6">
                    <label htmlFor="name" className="block text-sm font-medium text-nextstep-text-primary">
                      Name
                    </label>
                    <div className="mt-1">
                      <input
                        type="text"
                        name="name"
                        id="name"
                        value={formData.name}
                        onChange={handleChange}
                        className="nextstep-input block w-full px-3 py-2"
                      />
                    </div>
                    <p className="mt-2 text-sm text-nextstep-text-muted">
                      Optional: Leave blank to use the repository name.
                    </p>
                  </div>

                  <div className="sm:col-span-6">
                    <label htmlFor="description" className="block text-sm font-medium text-nextstep-text-primary">
                      Description
                    </label>
                    <div className="mt-1">
                      <textarea
                        id="description"
                        name="description"
                        rows={3}
                        value={formData.description}
                        onChange={handleChange}
                        className="nextstep-input block w-full px-3 py-2"
                      />
                    </div>
                    <p className="mt-2 text-sm text-nextstep-text-muted">
                      Brief description of the repository. Will be extracted from README when using "Fetch Details".
                    </p>
                  </div>

                  <div className="sm:col-span-3">
                    <label htmlFor="transport" className="block text-sm font-medium text-nextstep-text-primary">
                      Transport
                    </label>
                    <div className="mt-1">
                      <select
                        id="transport"
                        name="transport"
                        value={formData.transport}
                        onChange={handleChange}
                        className="nextstep-input block w-full px-3 py-2"
                      >
                        <option value="stdio">stdio</option>
                        <option value="sse">sse</option>
                        <option value="http">http</option>
                        <option value="streamable_http">streamable_http</option>
                      </select>
                    </div>
                    <p className="mt-2 text-sm text-nextstep-text-muted">
                      The transport method for the MCP server.
                    </p>
                  </div>

                  <div className="sm:col-span-3">
                    <label htmlFor="command" className="block text-sm font-medium text-nextstep-text-primary">
                      Command
                    </label>
                    <div className="mt-1">
                      <input
                        type="text"
                        name="command"
                        id="command"
                        value={formData.command}
                        onChange={handleChange}
                        className="nextstep-input block w-full px-3 py-2"
                      />
                    </div>
                    <p className="mt-2 text-sm text-nextstep-text-muted">
                      Command to run the repository. Will be extracted from README when using "Fetch Details".
                    </p>
                  </div>

                  <div className="sm:col-span-6">
                    <label htmlFor="args" className="block text-sm font-medium text-nextstep-text-primary">
                      Arguments
                    </label>
                    <div className="mt-1 flex space-x-2">
                      <input
                        type="text"
                        id="new-arg"
                        value={newArg}
                        onChange={(e) => setNewArg(e.target.value)}
                        className="nextstep-input block w-full px-3 py-2"
                        placeholder="Add argument"
                      />
                      <button
                        type="button"
                        onClick={handleAddArg}
                        className="inline-flex items-center p-2 border border-transparent rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                      >
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                        </svg>
                      </button>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {formData.args.map((arg, index) => (
                        <div key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium bg-nextstep-border text-nextstep-text-primary">
                          {arg}
                          <button
                            type="button"
                            onClick={() => handleRemoveArg(index)}
                            className="ml-1.5 h-4 w-4 rounded-full inline-flex items-center justify-center text-nextstep-text-secondary hover:bg-gray-600 hover:text-nextstep-text-primary focus:outline-none focus:bg-primary-500 focus:text-white"
                          >
                            <svg className="h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                            </svg>
                          </button>
                        </div>
                      ))}
                    </div>
                    <p className="mt-2 text-sm text-nextstep-text-muted">
                      Arguments to pass to the command. Will be extracted from README when using "Fetch Details".
                    </p>
                  </div>

                  {/* Additional fields for non-stdio transport */}
                  {showAdditionalFields && (
                    <>
                      <div className="sm:col-span-6">
                        <label htmlFor="url" className="block text-sm font-medium text-nextstep-text-primary">
                          URL
                        </label>
                        <div className="mt-1">
                          <input
                            type="text"
                            name="url"
                            id="url"
                            value={formData.url}
                            onChange={handleChange}
                            className="nextstep-input block w-full px-3 py-2"
                          />
                        </div>
                        <p className="mt-2 text-sm text-nextstep-text-muted">
                          URL for the MCP server.
                        </p>
                      </div>

                      <div className="sm:col-span-3">
                        <label htmlFor="read_timeout_seconds" className="block text-sm font-medium text-nextstep-text-primary">
                          Read Timeout (seconds)
                        </label>
                        <div className="mt-1">
                          <input
                            type="number"
                            name="read_timeout_seconds"
                            id="read_timeout_seconds"
                            value={formData.read_timeout_seconds}
                            onChange={handleChange}
                            className="nextstep-input block w-full px-3 py-2"
                          />
                        </div>
                      </div>

                      <div className="sm:col-span-3">
                        <label htmlFor="read_transport_sse_timeout_seconds" className="block text-sm font-medium text-nextstep-text-primary">
                          SSE Timeout (seconds)
                        </label>
                        <div className="mt-1">
                          <input
                            type="number"
                            name="read_transport_sse_timeout_seconds"
                            id="read_transport_sse_timeout_seconds"
                            value={formData.read_transport_sse_timeout_seconds}
                            onChange={handleChange}
                            className="nextstep-input block w-full px-3 py-2"
                          />
                        </div>
                      </div>

                      <div className="sm:col-span-3">
                        <label htmlFor="headers" className="block text-sm font-medium text-nextstep-text-primary">
                          Headers (JSON)
                        </label>
                        <div className="mt-1">
                          <textarea
                            id="headers"
                            name="headers"
                            rows={2}
                            value={formData.headers}
                            onChange={handleChange}
                            className="nextstep-input block w-full px-3 py-2"
                            placeholder="{}"
                          />
                        </div>
                      </div>

                      <div className="sm:col-span-3">
                        <label htmlFor="api_key" className="block text-sm font-medium text-nextstep-text-primary">
                          API Key
                        </label>
                        <div className="mt-1">
                          <input
                            type="text"
                            name="api_key"
                            id="api_key"
                            value={formData.api_key}
                            onChange={handleChange}
                            className="nextstep-input block w-full px-3 py-2"
                          />
                        </div>
                      </div>

                      <div className="sm:col-span-6">
                        <label htmlFor="roots_table" className="block text-sm font-medium text-nextstep-text-primary">
                          Roots Table
                        </label>
                        <div className="mt-1">
                          <input
                            type="text"
                            name="roots_table"
                            id="roots_table"
                            value={formData.roots_table}
                            onChange={handleChange}
                            className="nextstep-input block w-full px-3 py-2"
                          />
                        </div>
                        <p className="mt-2 text-sm text-nextstep-text-muted">
                          Name of the table containing roots for this server.
                        </p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>

            {error && (
              <div className="pt-5 sm:col-span-6">
                <div className="rounded-md bg-red-900 bg-opacity-20 p-4 border border-red-600">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-red-400">{error}</h3>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div className="pt-5">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => navigate('/repositories')}
                  className="nextstep-button-secondary px-4 py-2 text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="ml-3 inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-gray-600 disabled:opacity-50"
                >
                  {loading ? 'Adding...' : 'Add Repository'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
} 