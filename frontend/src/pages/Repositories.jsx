import { useState, useEffect } from 'preact/hooks';
import { getRepositories, deleteRepository } from '../services/api';
import RepositoryCard from '../components/RepositoryCard';
import RepositorySearch from '../components/RepositorySearch';

export default function Repositories() {
  const [repositories, setRepositories] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRepositories = async () => {
    try {
      setLoading(true);
      const data = await getRepositories();
      setRepositories(data);
    } catch (error) {
      console.error('Error fetching repositories:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRepositories();
  }, []);

  const handleDelete = async (name) => {
    if (window.confirm(`Are you sure you want to delete the repository "${name}"?`)) {
      try {
        await deleteRepository(name);
        fetchRepositories();
      } catch (error) {
        console.error('Error deleting repository:', error);
      }
    }
  };

  return (
    <div class="container">
      <div class="pb-5 border-b border-gray-200 sm:flex sm:items-center sm:justify-between">
        <h1 class="text-3xl font-bold leading-tight text-gray-900">Repositories</h1>
        <div class="mt-3 sm:mt-0 sm:ml-4">
          <a
            href="/add-github-repo"
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Add Repository
          </a>
        </div>
      </div>

      {/* Repository Search Component */}
      <div class="mt-6">
        <RepositorySearch />
      </div>

      {loading ? (
        <div class="mt-6 flex justify-center">
          <div class="w-12 h-12 border-t-2 border-b-2 border-blue-500 rounded-full animate-spin"></div>
        </div>
      ) : repositories.length === 0 ? (
        <div class="mt-6 text-center bg-white shadow rounded-lg p-8">
          <svg
            class="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
          <h3 class="mt-2 text-sm font-medium text-gray-900">No repositories</h3>
          <p class="mt-1 text-sm text-gray-500">Get started by adding a new repository.</p>
          <div class="mt-6">
            <a
              href="/add-github-repo"
              class="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Add Repository
            </a>
          </div>
        </div>
      ) : (
        <div class="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {repositories.map((repository) => (
            <RepositoryCard
              key={repository.id}
              repository={repository}
              onDelete={handleDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
} 