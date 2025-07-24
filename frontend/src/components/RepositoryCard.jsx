import { useState } from 'preact/hooks';
import { MoreVertical } from 'preact-feather';

export default function RepositoryCard({ repository, onDelete }) {
  const [showDropdown, setShowDropdown] = useState(false);

  const handleEdit = () => {
    // Assuming repository.id is available. If not, we can use repository.name
    // and adjust the target page to fetch by name.
    // For now, let's assume /edit-repository/:id is the route or similar
    // Or, more aligned with existing patterns, navigate to review and prefill.
    // Let's use a placeholder for navigation for now, can be changed to history.push
    window.location.href = `/review-repository?repo_name=${encodeURIComponent(repository.name)}`;
    setShowDropdown(false);
  };

  const handleDelete = () => {
    onDelete(repository.name);
    setShowDropdown(false);
  };

  // Determine deployment status class based on new requirements
  let statusClass = 'bg-gray-100 text-gray-800'; // Default
  let statusText = repository.deployment_status ? repository.deployment_status.replace(/_/g, ' ') : 'Unknown';

  if (repository.deployment_status === 'deployed') {
    statusClass = 'bg-gray-200 text-gray-700'; // Deployed status in gray
    statusText = 'Deployed';
  } else if (repository.deployment_status === 'ready') {
    statusClass = 'bg-green-100 text-green-800'; // Ready status in green
    statusText = 'Ready';
  } else if (repository.deployment_status === 'failed_to_deploy' || repository.deployment_status === 'failed_to_update_status_before_deploy' || repository.deployment_status === 'error_checking_status') {
    statusClass = 'bg-red-100 text-red-800';
  } else if (repository.deployment_status === 'deploying') {
    statusClass = 'bg-yellow-100 text-yellow-800';
  }

  return (
    <div class="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      <div class="px-4 py-5 sm:p-6">
        <div class="flex items-center">
          <div class="flex-shrink-0 bg-blue-800 bg-opacity-20 rounded-md p-3">
            <span class="text-xl" aria-hidden="true">📁</span>
          </div>
          <div class="ml-5 w-0 flex-1">
            <dl>
              <dt class="text-sm font-medium text-gray-500 truncate">{repository.name}</dt>
              <dd>
                <div class="text-lg font-medium text-gray-900">{repository.command}</div>
              </dd>
            </dl>
          </div>
          <div class="ml-4 flex-shrink-0 relative">
            <button
              type="button"
              onClick={() => setShowDropdown(!showDropdown)}
              class="inline-flex items-center p-2 border border-transparent rounded-full text-gray-500 hover:text-gray-700 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <MoreVertical size={20} />
              <span class="sr-only">Open options</span>
            </button>
            {showDropdown && (
              <div class="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
                <div class="py-1" role="menu" aria-orientation="vertical" aria-labelledby="options-menu">
                  <button
                    onClick={handleEdit}
                    class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                    role="menuitem"
                  >
                    Edit
                  </button>
                  {repository.deploy_as_container && (
                    <button
                      onClick={() => {
                        window.location.href = `/deploy-container/${encodeURIComponent(repository.name)}`;
                        setShowDropdown(false);
                      }}
                      class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                      role="menuitem"
                    >
                      Deploy
                    </button>
                  )}
                  <button
                    onClick={handleDelete}
                    class="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 hover:text-red-700"
                    role="menuitem"
                  >
                    Delete
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
        <div class="mt-4">
          <p class="text-sm text-gray-500 line-clamp-2">{repository.description}</p>
        </div>
        <div class="mt-4">
          <div class="text-sm text-gray-400">Arguments:</div>
          <div class="mt-1 flex flex-wrap gap-2">
            {repository.args && repository.args.length > 0 ? (
              repository.args.map((arg, index) => (
                <span key={index} class="inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium bg-gray-100 text-gray-800">
                  {arg}
                </span>
              ))
            ) : (
              <span class="text-sm text-gray-400">No arguments</span>
            )}
          </div>
        </div>

        {/* Deployment Status Section */}
        {repository.deploy_as_container && repository.deployment_status && (
            <div class="mt-4 pt-4 border-t border-gray-200">
                <div class="text-sm font-medium text-gray-500">Deployment Status:</div>
                <div class="mt-1">
                    <span 
                        class={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}`}
                    >
                        {statusText}
                    </span>
                </div>
            </div>
        )}
      </div>
    </div>
  );
} 