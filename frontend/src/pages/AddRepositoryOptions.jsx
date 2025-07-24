import { Link } from 'preact-router/match';

export default function AddRepositoryOptions() {
  return (
    <div class="container">
      <div class="pb-5 border-b border-gray-200">
        <h1 class="text-3xl font-bold leading-tight text-gray-900">Add New Server</h1>
        <p class="mt-2 text-sm text-gray-500">How would you like to add a new MCP server?</p>
      </div>

      <div class="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-2">
        {/* Card 1: Add from GitHub */}
        <div class="bg-white shadow rounded-lg overflow-hidden">
          <Link href="/add-github-repo" class="block hover:bg-gray-50">
            <div class="p-6">
              <div class="flex items-center">
                <div class="flex-shrink-0 bg-blue-600 rounded-md p-3">
                  {/* GitHub Icon (simplified) */}
                  <svg class="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path fill-rule="evenodd" d="M12 2C6.477 2 2 6.477 2 12c0 4.418 2.865 8.166 6.839 9.489.5.092.682-.217.682-.483 0-.237-.009-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.031-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.026 2.747-1.026.546 1.379.202 2.398.1 2.651.64.7 1.03 1.595 1.03 2.688 0 3.848-2.338 4.695-4.566 4.942.359.309.678.922.678 1.856 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.001 10.001 0 0022 12c0-5.523-4.477-10-10-10z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-4">
                  <h3 class="text-lg font-medium text-gray-900">Add from GitHub</h3>
                  <p class="mt-1 text-sm text-gray-500">Import a repository from GitHub. We will try to auto-configure it as an MCP server.</p>
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* Card 2: Connect External MCP Server */}
        <div class="bg-white shadow rounded-lg overflow-hidden">
          <Link href="/add-external-mcp-server" class="block hover:bg-gray-50">
            <div class="p-6">
              <div class="flex items-center">
                <div class="flex-shrink-0 bg-green-600 rounded-md p-3">
                  {/* External Server Icon (simplified - e.g., plug) */}
                  <svg class="h-6 w-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                  </svg>
                </div>
                <div class="ml-4">
                  <h3 class="text-lg font-medium text-gray-900">Connect External MCP Server</h3>
                  <p class="mt-1 text-sm text-gray-500">Connect to an existing, already running MCP server by providing its details.</p>
                </div>
              </div>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
} 