import { useState } from 'preact/hooks';
import { fetchRepositoryDetails } from '../services/api';

export default function GitHubRepoInput() {
  const [repoUrl, setRepoUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!repoUrl || !repoUrl.includes('github.com')) {
      setError('Please enter a valid GitHub repository URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Fetch repo details and then navigate to review page with data
      const details = await fetchRepositoryDetails(repoUrl);
      
      // Create state object to pass in URL
      const stateData = { details, repoUrl };
      const stateParam = encodeURIComponent(JSON.stringify(stateData));
      
      // Navigate to review page with query parameter
      window.location.href = `/review-repository?state=${stateParam}`;
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch repository details. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div>
      <div class="pb-5 border-b border-gray-200">
        <h1 class="text-3xl font-bold leading-tight">Add GitHub Repository</h1>
      </div>

      <div class="mt-6">
        <div class="bg-white shadow rounded-lg p-6">
          <form onSubmit={handleSubmit} class="space-y-8">
            <div>
              <p class="text-sm text-gray-600 mb-6">
                Enter a GitHub repository URL to add. The system will automatically extract
                information from the README to create an MCP server configuration.
              </p>
              
              <div class="mt-6">
                <label for="repo_url" class="block text-sm font-medium text-gray-700">
                  GitHub Repository URL
                </label>
                <div class="mt-1">
                  <input
                    type="text"
                    id="repo_url"
                    name="repo_url"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/username/repo.git"
                    class="block w-full px-3 py-3 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
                <p class="mt-2 text-sm text-gray-500">
                  Example: https://github.com/username/repository.git
                </p>
              </div>
            </div>

            {error && (
              <div class="rounded-md bg-red-100 p-4 border border-red-300">
                <div class="flex">
                  <div class="flex-shrink-0">
                    <svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div class="ml-3">
                    <h3 class="text-sm font-medium text-red-700">{error}</h3>
                  </div>
                </div>
              </div>
            )}

            <div class="pt-5">
              <div class="flex justify-end">
                <a
                  href="/"
                  class="px-4 py-2 text-sm font-medium border border-gray-300 rounded-md shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  Cancel
                </a>
                <button
                  type="submit"
                  disabled={loading}
                  class="ml-3 inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Continue'}
                </button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
} 