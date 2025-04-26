import { useState, useEffect } from 'preact/hooks';
import { searchRepositories, getQdrantStatus } from '../services/api';

const RepositorySearch = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('unknown');
  const [checkingStatus, setCheckingStatus] = useState(true);

  useEffect(() => {
    checkQdrantStatus();
  }, []);

  const checkQdrantStatus = async () => {
    try {
      setCheckingStatus(true);
      const status = await getQdrantStatus();
      setConnectionStatus(status.status);
    } catch (error) {
      console.error('Error checking Qdrant status:', error);
      setConnectionStatus('disconnected');
    } finally {
      setCheckingStatus(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    try {
      setLoading(true);
      setError('');
      
      // Check status before searching
      await checkQdrantStatus();
      
      if (connectionStatus !== 'connected') {
        setError('Vector search unavailable: Qdrant is not connected.');
        setResults([]);
        return;
      }
      
      const data = await searchRepositories(query, 5);
      setResults(data);
    } catch (error) {
      setError('Failed to search repositories. Please try again.');
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score) => {
    return (score * 100).toFixed(1) + '%';
  };

  return (
    <div class="mb-4">
      {connectionStatus === 'disconnected' && (
        <div class="p-3 bg-yellow-100 border border-yellow-400 text-yellow-700 rounded mb-2">
          Vector search is currently unavailable because Qdrant is not connected.
          <a href="/vector-settings" class="ml-2 text-blue-600 hover:underline">
            Check settings
          </a>
        </div>
      )}
      
      <form onSubmit={handleSearch} class="w-full">
        <div class="relative">
          <input
            type="text"
            class="w-full px-4 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Search repositories with natural language..."
            value={query}
            onInput={(e) => setQuery(e.target.value)}
          />
          <button 
            type="submit" 
            class="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 text-blue-500 hover:text-blue-700 focus:outline-none"
            disabled={loading || !query.trim() || checkingStatus || connectionStatus === 'disconnected'}
          >
            {loading ? (
              <div class="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <span class="text-lg">🔍</span>
            )}
          </button>
        </div>
      </form>

      {error && (
        <div class="mt-1 text-red-500 text-sm">
          {error}
        </div>
      )}

      {results.length > 0 && (
        <div class="mt-2 bg-white border border-gray-200 rounded shadow">
          <ul>
            {results.map((repo, index) => (
              <li key={repo.name}>
                {index > 0 && <hr class="border-gray-200" />}
                <a
                  href={`/repositories?name=${encodeURIComponent(repo.name)}`}
                  class="block px-4 py-3 text-inherit no-underline hover:bg-gray-50"
                >
                  <div class="flex items-center justify-between">
                    <div class="flex items-center">
                      <span class="mr-2">💻</span>
                      <span class="font-medium">{repo.name}</span>
                    </div>
                    <span class="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded-full border border-blue-200">
                      Match: {formatScore(repo.score)}
                    </span>
                  </div>
                  <div class="mt-1 text-sm text-gray-600">{repo.description}</div>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default RepositorySearch; 