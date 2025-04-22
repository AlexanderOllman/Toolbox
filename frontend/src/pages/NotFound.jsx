import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="text-center">
        <h1 className="text-9xl font-bold text-nextstep-text-primary">404</h1>
        <p className="mt-4 text-xl text-nextstep-text-secondary">Page not found</p>
        <p className="mt-2 text-base text-nextstep-text-muted">
          Sorry, we couldn't find the page you're looking for.
        </p>
        <div className="mt-8">
          <Link
            to="/"
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Return to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
} 