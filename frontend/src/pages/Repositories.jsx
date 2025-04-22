import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
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
    <div className="nextstep-container">
      <div className="pb-5 border-b border-nextstep-border sm:flex sm:items-center sm:justify-between">
        <h1 className="text-3xl font-bold leading-tight text-nextstep-text-primary">Repositories</h1>
        <div className="mt-3 sm:mt-0 sm:ml-4">
          <Link
            to="/add-github-repo"
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Add Repository
          </Link>
        </div>
      </div>

      {/* Repository Search Component */}
      <div className="mt-6">
        <RepositorySearch />
      </div>

      {loading ? (
        <div className="mt-6 flex justify-center">
          <div className="w-12 h-12 border-t-2 border-b-2 border-primary-500 rounded-full animate-spin"></div>
        </div>
      ) : repositories.length === 0 ? (
        <div className="mt-6 text-center nextstep-card p-8">
          <svg
            className="mx-auto h-12 w-12 text-nextstep-text-muted"
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
          <h3 className="mt-2 text-sm font-medium text-nextstep-text-primary">No repositories</h3>
          <p className="mt-1 text-sm text-nextstep-text-secondary">Get started by adding a new repository.</p>
          <div className="mt-6">
            <Link
              to="/add-github-repo"
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Add Repository
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-6 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
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