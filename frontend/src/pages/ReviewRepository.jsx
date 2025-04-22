import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { createRepository } from '../services/api';

export default function ReviewRepository() {
  const navigate = useNavigate();
  const location = useLocation();
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

  // Load details from navigation state
  useEffect(() => {
    if (location.state?.details && location.state?.repoUrl) {
      const { details, repoUrl } = location.state;
      setFormData({
        name: details.name || '',
        repo_url: repoUrl,
        description: details.description || '',
        command: details.command || '',
        args: details.args || []
      });
    } else {
      // If no data was passed, redirect back to input page
      navigate('/add-github-repo');
    }
  }, [location, navigate]);

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
      navigate('/repositories');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add repository. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="pb-5 border-b border-nextstep-border">
        <h1 className="text-3xl font-bold leading-tight">Review Repository</h1>
      </div>

      <div className="mt-6">
        <div className="nextstep-card p-6">
          <div className="mb-6">
            <div className="flex items-center space-x-3 mb-4">
              <div className="bg-primary-800 bg-opacity-20 p-2 rounded-md">
                <svg className="h-6 w-6 text-primary-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-lg font-medium text-nextstep-text-primary">AI-Generated Repository Information</h2>
            </div>
            <p className="text-sm text-nextstep-text-secondary">
              The following information was extracted from the repository by GPT. 
              You can review and edit this information before adding the repository.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-8 divide-y divide-nextstep-border">
            <div className="space-y-8">
              <div className="mt-6 grid grid-cols-1 gap-y-6 gap-x-4 sm:grid-cols-6">
                <div className="sm:col-span-6">
                  <label htmlFor="repo_url" className="block text-sm font-medium text-nextstep-text-primary">
                    Repository URL
                  </label>
                  <div className="mt-1">
                    <input
                      type="text"
                      name="repo_url"
                      id="repo_url"
                      value={formData.repo_url}
                      readOnly
                      className="nextstep-input block w-full px-3 py-2 bg-nextstep-border text-opacity-75"
                    />
                  </div>
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
                </div>

                <div className="sm:col-span-6">
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
                </div>
              </div>
            </div>

            {error && (
              <div className="pt-5">
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
                  onClick={() => navigate('/add-github-repo')}
                  className="nextstep-button-secondary px-4 py-2 text-sm font-medium"
                >
                  Back
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