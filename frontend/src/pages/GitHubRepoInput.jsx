import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchRepositoryDetails } from '../services/api';

export default function GitHubRepoInput() {
  const navigate = useNavigate();
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
      navigate('/review-repository', { 
        state: { 
          details,
          repoUrl 
        } 
      });
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch repository details. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="pb-5 border-b border-nextstep-border">
        <h1 className="text-3xl font-bold leading-tight">Add GitHub Repository</h1>
      </div>

      <div className="mt-6">
        <div className="nextstep-card p-6">
          <form onSubmit={handleSubmit} className="space-y-8">
            <div>
              <p className="text-sm text-nextstep-text-secondary mb-6">
                Enter a GitHub repository URL to add. The system will automatically extract
                information from the README to create an MCP server configuration.
              </p>
              
              <div className="mt-6">
                <label htmlFor="repo_url" className="block text-sm font-medium text-nextstep-text-primary">
                  GitHub Repository URL
                </label>
                <div className="mt-1">
                  <input
                    type="text"
                    id="repo_url"
                    name="repo_url"
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    placeholder="https://github.com/username/repo.git"
                    className="nextstep-input block w-full px-3 py-3 rounded-md"
                    required
                  />
                </div>
                <p className="mt-2 text-sm text-nextstep-text-muted">
                  Example: https://github.com/username/repository.git
                </p>
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-900 bg-opacity-20 p-4 border border-red-600">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-400">{error}</h3>
                  </div>
                </div>
              </div>
            )}

            <div className="pt-5">
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="nextstep-button-secondary px-4 py-2 text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="ml-3 inline-flex justify-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-gray-600 disabled:opacity-50"
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