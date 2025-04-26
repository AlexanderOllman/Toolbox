export default function NotFound() {
  return (
    <div class="flex flex-col items-center justify-center py-16">
      <div class="text-center">
        <h1 class="text-9xl font-bold text-gray-800">404</h1>
        <p class="mt-4 text-xl text-gray-600">Page not found</p>
        <p class="mt-2 text-base text-gray-500">
          Sorry, we couldn't find the page you're looking for.
        </p>
        <div class="mt-8">
          <a
            href="/"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Return to Dashboard
          </a>
        </div>
      </div>
    </div>
  );
} 