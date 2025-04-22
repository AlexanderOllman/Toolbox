import { FolderIcon, TrashIcon } from '@heroicons/react/24/outline';

export default function RepositoryCard({ repository, onDelete }) {
  return (
    <div className="nextstep-card overflow-hidden">
      <div className="px-4 py-5 sm:p-6">
        <div className="flex items-center">
          <div className="flex-shrink-0 bg-primary-800 bg-opacity-20 rounded-md p-3">
            <FolderIcon className="h-6 w-6 text-primary-400" aria-hidden="true" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="text-sm font-medium text-nextstep-text-secondary truncate">{repository.name}</dt>
              <dd>
                <div className="text-lg font-medium text-nextstep-text-primary">{repository.command}</div>
              </dd>
            </dl>
          </div>
          <div className="ml-4 flex-shrink-0">
            <button
              type="button"
              onClick={() => onDelete(repository.name)}
              className="inline-flex items-center p-1 border border-transparent rounded-full text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
            >
              <TrashIcon className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>
        <div className="mt-4">
          <p className="text-sm text-nextstep-text-secondary line-clamp-2">{repository.description}</p>
        </div>
        <div className="mt-4">
          <div className="text-sm text-nextstep-text-muted">Arguments:</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {repository.args && repository.args.length > 0 ? (
              repository.args.map((arg, index) => (
                <span key={index} className="inline-flex items-center px-2.5 py-0.5 rounded-md text-sm font-medium bg-nextstep-border text-nextstep-text-primary">
                  {arg}
                </span>
              ))
            ) : (
              <span className="text-sm text-nextstep-text-muted">No arguments</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
} 