import { useState, useEffect } from 'preact/hooks';
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
      <div class="pb-5 border-b border-gray-200">
        <h1 class="text-3xl font-bold leading-tight">Dashboard</h1>
      </div>

      {loading ? (
        <div class="mt-6 flex justify-center">
          <div class="w-12 h-12 border-t-2 border-b-2 border-blue-500 rounded-full animate-spin"></div>
        </div>
      ) : (
        <div class="mt-6">
          <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {/* Repositories stats card */}
            <div class="bg-white shadow rounded-lg overflow-hidden">
              <div class="bg-gradient-to-r from-blue-500 to-indigo-600 px-4 py-5 sm:p-6">
                <div class="flex items-center">
                  <div class="flex-shrink-0 bg-blue-800 bg-opacity-20 rounded-md p-3">
                    <svg class="h-6 w-6 text-blue-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                    </svg>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-blue-100 truncate">Repositories</dt>
                      <dd>
                        <div class="text-lg font-medium text-white">{stats.repositories}</div>
                      </dd>
                    </dl>
                  </div>
                </div>
                <div class="mt-5">
                  <a
                    href="/repositories"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-700 hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    View all
                  </a>
                </div>
              </div>
            </div>

            {/* Add Repository card */}
            <div class="bg-white shadow rounded-lg overflow-hidden">
              <div class="bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-5 sm:p-6">
                <div class="flex items-center">
                  <div class="flex-shrink-0 bg-green-800 bg-opacity-20 rounded-md p-3">
                    <svg class="h-6 w-6 text-green-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-green-100 truncate">Add Repository</dt>
                      <dd>
                        <div class="text-lg font-medium text-white">New Repo</div>
                      </dd>
                    </dl>
                  </div>
                </div>
                <div class="mt-5">
                  <a
                    href="/add-github-repo"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-green-700 hover:bg-green-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                  >
                    Add New
                  </a>
                </div>
              </div>
            </div>

            {/* Configuration card */}
            <div class="bg-white shadow rounded-lg overflow-hidden">
              <div class="bg-gradient-to-r from-purple-500 to-indigo-600 px-4 py-5 sm:p-6">
                <div class="flex items-center">
                  <div class="flex-shrink-0 bg-purple-800 bg-opacity-20 rounded-md p-3">
                    <svg class="h-6 w-6 text-purple-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <div class="ml-5 w-0 flex-1">
                    <dl>
                      <dt class="text-sm font-medium text-purple-100 truncate">Configuration</dt>
                      <dd>
                        <div class="text-lg font-medium text-white">YAML/JSON</div>
                      </dd>
                    </dl>
                  </div>
                </div>
                <div class="mt-5">
                  <a
                    href="/config"
                    class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-purple-700 hover:bg-purple-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500"
                  >
                    View Config
                  </a>
                </div>
              </div>
            </div>
          </div>
          
          {/* Semantic Search Section */}
          <div class="bg-white shadow rounded-lg overflow-hidden mt-6">
            <div class="bg-gradient-to-r from-gray-50 to-white px-4 py-5 sm:p-6">
              <h2 class="text-xl font-medium text-gray-900 mb-4">Semantic Search</h2>
              <p class="text-sm text-gray-600 mb-4">
                Search for repositories based on semantic relation to your description
              </p>
              
              <form onSubmit={handleSearch} class="mb-4">
                <div class="flex">
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Describe what you're looking for..."
                    class="flex-grow px-4 py-2 border border-gray-300 rounded-l focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white text-gray-900"
                  />
                  <button
                    type="submit"
                    disabled={searchLoading || !query.trim()}
                    class="px-4 py-2 bg-blue-600 text-white rounded-r hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    {searchLoading ? 'Searching...' : 'Search'}
                  </button>
                </div>
              </form>

              {searchError && (
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                  {searchError}
                </div>
              )}

              {searchResults.length > 0 && (
                <div>
                  <h3 class="text-lg font-medium text-gray-900 mb-2">Top 5 Results</h3>
                  <div class="space-y-4">
                    {searchResults.map((repo, index) => (
                      <div key={index} class="border border-gray-200 rounded p-4">
                        <div class="flex justify-between items-start">
                          <h4 class="text-lg font-medium text-gray-900">{repo.name}</h4>
                          <span class="text-sm bg-blue-100 text-blue-800 py-1 px-2 rounded">
                            Score: {(repo.score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <p class="mt-1 text-gray-600">{repo.description}</p>
                        <div class="mt-2">
                          <span class="text-sm font-medium text-gray-900">Command: </span>
                          <code class="text-sm bg-gray-100 text-gray-800 px-2 py-1 rounded">
                            {repo.command}
                          </code>
                        </div>
                        {repo.args && repo.args.length > 0 && (
                          <div class="mt-2">
                            <span class="text-sm font-medium text-gray-900">Args: </span>
                            <code class="text-sm bg-gray-100 text-gray-800 px-2 py-1 rounded">
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