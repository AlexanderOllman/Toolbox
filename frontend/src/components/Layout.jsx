const navItems = [
  { name: 'Dashboard', to: '/', icon: 'home' },
  { name: 'Repositories', to: '/repositories', icon: 'folder' },
  { name: 'Configuration', to: '/config', icon: 'settings' },
  { name: 'Vector DB', to: '/vector-settings', icon: 'database' },
];

// Modern SVG icon component
const Icon = ({ icon, className = "" }) => {
  const icons = {
    home: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={`w-5 h-5 ${className}`}>
        <path d="M11.47 3.84a.75.75 0 011.06 0l8.69 8.69a.75.75 0 101.06-1.06l-8.689-8.69a2.25 2.25 0 00-3.182 0l-8.69 8.69a.75.75 0 001.061 1.06l8.69-8.69z" />
        <path d="M12 5.432l8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 01-.75-.75v-4.5a.75.75 0 00-.75-.75h-3a.75.75 0 00-.75.75V21a.75.75 0 01-.75.75H5.625a1.875 1.875 0 01-1.875-1.875v-6.198a2.29 2.29 0 00.091-.086L12 5.43z" />
      </svg>
    ),
    folder: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={`w-5 h-5 ${className}`}>
        <path d="M19.5 21a3 3 0 003-3v-4.5a3 3 0 00-3-3h-15a3 3 0 00-3 3V18a3 3 0 003 3h15zM1.5 10.146V6a3 3 0 013-3h5.379a2.25 2.25 0 011.59.659l2.122 2.121c.14.141.331.22.53.22H19.5a3 3 0 013 3v1.146A4.483 4.483 0 0019.5 9h-15a4.483 4.483 0 00-3 1.146z" />
      </svg>
    ),
    settings: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={`w-5 h-5 ${className}`}>
        <path fill-rule="evenodd" d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 00-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 00-2.282.819l-.922 1.597a1.875 1.875 0 00.432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 000 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 00-.432 2.385l.922 1.597a1.875 1.875 0 002.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.986.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 002.28-.819l.923-1.597a1.875 1.875 0 00-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 000-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 00-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 00-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 00-1.85-1.567h-1.843zM12 15.75a3.75 3.75 0 100-7.5 3.75 3.75 0 000 7.5z" clip-rule="evenodd" />
      </svg>
    ),
    database: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={`w-5 h-5 ${className}`}>
        <path d="M21 6.375c0 2.692-4.03 4.875-9 4.875S3 9.067 3 6.375 7.03 1.5 12 1.5s9 2.183 9 4.875z" />
        <path d="M12 12.75s2.25.75 4.5.75c1.513 0 2.938-.237 4.5-.75v5.25c0 2.692-4.03 4.875-9 4.875s-9-2.183-9-4.875V12.75c1.562.513 2.987.75 4.5.75 2.25 0 4.5-.75 4.5-.75z" />
      </svg>
    ),
    code: (
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={`w-5 h-5 ${className}`}>
        <path fill-rule="evenodd" d="M14.447 3.027a.75.75 0 01.527.92l-4.5 16.5a.75.75 0 01-1.448-.394l4.5-16.5a.75.75 0 01.921-.526zM16.72 6.22a.75.75 0 011.06 0l5.25 5.25a.75.75 0 010 1.06l-5.25 5.25a.75.75 0 11-1.06-1.06L21.44 12l-4.72-4.72a.75.75 0 010-1.06zm-9.44 0a.75.75 0 010 1.06L2.56 12l4.72 4.72a.75.75 0 11-1.06 1.06L.97 12.53a.75.75 0 010-1.06l5.25-5.25a.75.75 0 011.06 0z" clip-rule="evenodd" />
      </svg>
    ),
  };
  
  return icons[icon] || (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class={`w-5 h-5 ${className}`}>
      <path fill-rule="evenodd" d="M4.5 7.5a3 3 0 013-3h9a3 3 0 013 3v9a3 3 0 01-3 3h-9a3 3 0 01-3-3v-9z" clip-rule="evenodd" />
    </svg>
  );
};

export default function Layout({ children }) {
  return (
    <div class="h-screen flex overflow-hidden bg-nextstep-background">
      {/* Sidebar */}
      <div class="hidden md:flex md:flex-shrink-0">
        <div class="flex flex-col w-64">
          <div class="flex flex-col h-0 flex-1 bg-white border-r border-gray-200">
            <div class="flex items-center h-16 flex-shrink-0 px-4 bg-nextstep-gradient">
              <div class="flex items-center">
                <Icon icon="code" className="text-white" />
                <span class="ml-2 text-white text-xl font-heading font-semibold">Toolbox</span>
              </div>
            </div>
            <div class="flex-1 flex flex-col overflow-y-auto border-r border-nextstep-border bg-white">
              <nav class="flex-1 px-2 py-4 space-y-1">
                {navItems.map((item) => {
                  const isActive = typeof window !== 'undefined' && window.location.pathname === item.to;
                  return (
                    <a
                      key={item.name}
                      href={item.to}
                      class={`${
                        isActive
                          ? 'bg-primary-50 text-primary-600 border-l-4 border-primary-500'
                          : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                      } group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-all duration-200`}
                    >
                      <div class={`mr-3 ${isActive ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'}`}>
                        <Icon icon={item.icon} />
                      </div>
                      {item.name}
                    </a>
                  );
                })}
              </nav>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div class="flex flex-col w-0 flex-1 overflow-hidden">
        <main class="flex-1 relative z-0 overflow-y-auto focus:outline-none">
          <div class="py-6">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
} 