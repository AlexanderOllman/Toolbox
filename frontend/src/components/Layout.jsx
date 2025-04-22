import { Outlet, NavLink } from 'react-router-dom';
import { 
  HomeIcon, 
  FolderIcon, 
  CodeBracketSquareIcon,
  Cog6ToothIcon,
  ServerIcon
} from '@heroicons/react/24/outline';

const navItems = [
  { name: 'Dashboard', to: '/', icon: HomeIcon },
  { name: 'Repositories', to: '/repositories', icon: FolderIcon },
  { name: 'Configuration', to: '/config', icon: Cog6ToothIcon },
  { name: 'Vector DB', to: '/vector-settings', icon: ServerIcon },
];

export default function Layout() {
  return (
    <div className="h-screen flex overflow-hidden bg-nextstep-background">
      {/* Sidebar */}
      <div className="hidden md:flex md:flex-shrink-0">
        <div className="flex flex-col w-64">
          <div className="flex flex-col h-0 flex-1 bg-nextstep-card border-r border-nextstep-border">
            <div className="flex items-center h-16 flex-shrink-0 px-4 bg-nextstep-gradient border-b border-nextstep-border">
              <div className="flex items-center">
                <CodeBracketSquareIcon className="h-8 w-8 text-primary-400" />
                <span className="ml-2 text-nextstep-text-primary text-xl font-semibold">Toolbox</span>
              </div>
            </div>
            <div className="flex-1 flex flex-col overflow-y-auto">
              <nav className="flex-1 px-2 py-4 space-y-1">
                {navItems.map((item) => (
                  <NavLink
                    key={item.name}
                    to={item.to}
                    className={({ isActive }) =>
                      `${
                        isActive
                          ? 'bg-primary-600 text-white'
                          : 'text-nextstep-text-secondary hover:bg-nextstep-border hover:text-nextstep-text-primary'
                      } group flex items-center px-2 py-2 text-sm font-medium rounded-md`
                    }
                  >
                    <item.icon
                      className="mr-3 flex-shrink-0 h-6 w-6"
                      aria-hidden="true"
                    />
                    {item.name}
                  </NavLink>
                ))}
              </nav>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col w-0 flex-1 overflow-hidden">
        <main className="flex-1 relative z-0 overflow-y-auto focus:outline-none">
          <div className="py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 md:px-8">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
} 