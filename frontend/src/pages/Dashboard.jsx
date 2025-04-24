import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getRepositories, searchRepositories } from '../services/api';

export default function Dashboard() {
  const [stats, setStats] = useState({
    repositories: 0,
  });
  const [loading, setLoading] = useState(true);
  
  // Semantic search state
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const repositories = await getRepositories();
        setStats({
          repositories: repositories.length,
        });
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);
  
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearchLoading(true);
    setSearchError(null);
    
    try {
      const results = await searchRepositories(query, 5);
      setSearchResults(results);
    } catch (error) {
      console.error('Error searching repositories:', error);
      setSearchError('Failed to search repositories. Please try again.');
    } finally {
      setSearchLoading(false);
    }
  };

  return (
    <div>
      <div className="pb-5 border-b border-nextstep-border">
        <h1 className="text-3xl font-bold leading-tight">Dashboard</h1>
      </div>

      {loading ? (
        <div className="mt-6 flex justify-center">
          <div className="w-12 h-12 border-t-2 border-b-2 border-primary-500 rounded-full animate-spin"></div>
        </div>
      ) : (
        <div className="mt-6">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {/* Repositories stats card */}
            <div className="nextstep-card overflow-hidden">
              <div className="nextstep-gradient px-4 py-5 sm:p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0 bg-primary-800 bg-opacity-20 rounded-md p-3">
                    <svg className="h-6 w-6 text-primary-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-nextstep-text-secondary truncate">Repositories</dt>
                      <dd>
                        <div className="text-lg font-medium text-nextstep-text-primary">{stats.repositories}</div>
                      </dd>
                    </dl>
                  </div>
                </div>
                <div className="mt-5">
                  <Link
                    to="/repositories"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    View all
                  </Link>
                </div>
              </div>
            </div>

            {/* Add Repository card */}
            <div className="nextstep-card overflow-hidden">
              <div className="nextstep-gradient px-4 py-5 sm:p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0 bg-green-800 bg-opacity-20 rounded-md p-3">
                    <svg className="h-6 w-6 text-green-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-nextstep-text-secondary truncate">Add Repository</dt>
                      <dd>
                        <div className="text-lg font-medium text-nextstep-text-primary">New Repo</div>
                      </dd>
                    </dl>
                  </div>
                </div>
                <div className="mt-5">
                  <Link
                    to="/add-github-repo"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    Add New
                  </Link>
                </div>
              </div>
            </div>

            {/* Configuration card */}
            <div className="nextstep-card overflow-hidden">
              <div className="nextstep-gradient px-4 py-5 sm:p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0 bg-purple-800 bg-opacity-20 rounded-md p-3">
                    <svg className="h-6 w-6 text-purple-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-nextstep-text-secondary truncate">Configuration</dt>
                      <dd>
                        <div className="text-lg font-medium text-nextstep-text-primary">YAML/JSON</div>
                      </dd>
                    </dl>
                  </div>
                </div>
                <div className="mt-5">
                  <Link
                    to="/config"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                  >
                    View Config
                  </Link>
                </div>
              </div>
            </div>
          </div>
          
          {/* Semantic Search Section */}
          <div className="nextstep-card overflow-hidden mt-6">
            <div className="nextstep-gradient px-4 py-5 sm:p-6">
              <h2 className="text-xl font-medium text-nextstep-text-primary mb-4">Semantic Search</h2>
              <p className="text-sm text-nextstep-text-secondary mb-4">
                Search for repositories based on semantic relation to your description
              </p>
              
              <form onSubmit={handleSearch} className="mb-4">
                <div className="flex">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Describe what you're looking for..."
                    className="flex-grow px-4 py-2 border border-gray-300 rounded-l focus:outline-none focus:ring-2 focus:ring-primary-500 bg-nextstep-input-bg text-nextstep-text-primary"
                  />
                  <button
                    type="submit"
                    disabled={searchLoading || !query.trim()}
                    className="px-4 py-2 bg-primary-600 text-white rounded-r hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {searchLoading ? 'Searching...' : 'Search'}
                  </button>
                </div>
              </form>

              {searchError && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {searchError}
                </div>
              )}

              {searchResults.length > 0 && (
                <div>
                  <h3 className="text-lg font-medium text-nextstep-text-primary mb-2">Top 5 Results</h3>
                  <div className="space-y-4">
                    {searchResults.map((repo, index) => (
                      <div key={index} className="border border-nextstep-border rounded p-4">
                        <div className="flex justify-between items-start">
                          <h4 className="text-lg font-medium text-nextstep-text-primary">{repo.name}</h4>
                          <span className="text-sm bg-primary-100 text-primary-800 py-1 px-2 rounded">
                            Score: {(repo.score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <p className="mt-1 text-nextstep-text-secondary">{repo.description}</p>
                        <div className="mt-2">
                          <span className="text-sm font-medium text-nextstep-text-primary">Command: </span>
                          <code className="text-sm bg-nextstep-code-bg text-nextstep-code-text px-2 py-1 rounded">
                            {repo.command}
                          </code>
                        </div>
                        {repo.args && repo.args.length > 0 && (
                          <div className="mt-2">
                            <span className="text-sm font-medium text-nextstep-text-primary">Args: </span>
                            <code className="text-sm bg-nextstep-code-bg text-nextstep-code-text px-2 py-1 rounded">
                              {repo.args.join(' ')}
                            </code>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
} 