export default function RepositoryCard({ repository, onDelete }) {
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
          <div class="ml-4 flex-shrink-0">
            <button
              type="button"
              onClick={() => onDelete(repository.name)}
              class="inline-flex items-center p-1 border border-transparent rounded-full text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <span class="text-lg" aria-hidden="true">🗑️</span>
            </button>
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
      </div>
    </div>
  );
} 