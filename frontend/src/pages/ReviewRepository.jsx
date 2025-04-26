import { useState, useEffect } from 'preact/hooks';
import { createRepository } from '../services/api';

export default function ReviewRepository() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    repo_url: '',
    description: '',
    command: '',
    args: []
  });
  const [newArg, setNewArg] = useState('');

  // Load details from URL query parameters
  useEffect(() => {
    // Get query parameters
    const urlParams = new URLSearchParams(window.location.search);
    const stateParam = urlParams.get('state');
    
    if (stateParam) {
      try {
        const state = JSON.parse(decodeURIComponent(stateParam));
        if (state.details && state.repoUrl) {
          const { details, repoUrl } = state;
          setFormData({
            name: details.name || '',
            repo_url: repoUrl,
            description: details.description || '',
            command: details.command || '',
            args: details.args || []
          });
        } else {
          // If no data was passed, redirect back to input page
          window.location.href = '/add-github-repo';
        }
      } catch (e) {
        console.error('Error parsing state parameter:', e);
        window.location.href = '/add-github-repo';
      }
    } else {
      // If no state parameter, redirect back to input page
      window.location.href = '/add-github-repo';
    }
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
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

    try {
      await createRepository(formData);
      window.location.href = '/repositories';
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add repository. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div class="pb-5 border-b border-gray-200">
        <h1 class="text-3xl font-bold leading-tight">Review Repository</h1>
      </div>

      <div class="mt-6">
        <div class="bg-white shadow rounded-lg p-6">
          <div class="mb-6">
            <div class="flex items-center space-x-3 mb-4">
              <div class="bg-blue-800 bg-opacity-20 p-2 rounded-md">
                <svg class="h-6 w-6 text-blue-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 class="text-lg font-medium text-gray-900">AI-Generated Repository Information</h2>
            </div>
            <p class="text-sm text-gray-600">
              The following information was extracted from the repository by GPT. 
              You can review and edit this information before adding the repository.
            </p>
          </div>

          <form onSubmit={handleSubmit} class="space-y-8 divide-y divide-gray-200">
            <div class="space-y-8">
              <div class="mt-6 grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div class="sm:col-span-6">
                  <label for="repo_url" class="block text-sm font-medium text-gray-700">
                    Repository URL
                  </label>
                  <div class="mt-1">
                    <input
                      type="text"
                      name="repo_url"
                      id="repo_url"
                      value={formData.repo_url}
                      readOnly
                      class="block w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-md shadow-sm text-gray-600"
                    />
                  </div>
                </div>

                <div class="sm:col-span-6">
                  <label for="name" class="block text-sm font-medium text-gray-700">
                    Name
                  </label>
                  <div class="mt-1">
                    <input
                      type="text"
                      name="name"
                      id="name"
                      value={formData.name}
                      onChange={handleChange}
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                <div class="sm:col-span-6">
                  <label for="description" class="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <div class="mt-1">
                    <textarea
                      id="description"
                      name="description"
                      rows={3}
                      value={formData.description}
                      onChange={handleChange}
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                <div class="sm:col-span-6">
                  <label for="command" class="block text-sm font-medium text-gray-700">
                    Command
                  </label>
                  <div class="mt-1">
                    <input
                      type="text"
                      name="command"
                      id="command"
                      value={formData.command}
                      onChange={handleChange}
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                <div class="sm:col-span-6">
                  <label for="args" class="block text-sm font-medium text-gray-700">
                    Arguments
                  </label>
                  <div class="mt-1 flex space-x-2">
                    <input
                      type="text"
                      id="new-arg"
                      value={newArg}
                      onChange={(e) => setNewArg(e.target.value)}
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                      placeholder="Add argument"
                    />
                    <button
                      type="button"
                      onClick={handleAddArg}
                      class="inline-flex items-center p-2 border border-transparent rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                      </svg>
                    </button>
                  </div>
                  <div class="mt-2 flex flex-wrap gap-2">
                    {formData.args.map((arg, index) => (
                      <div key={index} class="inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium bg-gray-100 text-gray-800">
                        {arg}
                        <button
                          type="button"
                          onClick={() => handleRemoveArg(index)}
                          class="ml-1.5 h-4 w-4 rounded-full inline-flex items-center justify-center text-gray-500 hover:bg-gray-300 hover:text-gray-700 focus:outline-none focus:bg-blue-500 focus:text-white"
                        >
                          <svg class="h-3 w-3" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {error && (
              <div class="pt-5">
                <div class="rounded-md bg-red-100 p-4 border border-red-300">
                  <div class="flex">
                    <div class="flex-shrink-0">
                      <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <div class="ml-3">
                      <h3 class="text-sm font-medium text-red-700">{error}</h3>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div class="pt-5">
              <div class="flex justify-end">
                <a
                  href="/add-github-repo"
                  class="px-4 py-2 text-sm font-medium border border-gray-300 rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Back
                </a>
                <button
                  type="submit"
                  disabled={loading}
                  class="ml-3 inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:opacity-50"
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