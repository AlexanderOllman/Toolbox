import { Router, Route } from 'preact-router';
import { lazy, Suspense } from 'preact/compat';

// Use lazy loading for components to reduce initial bundle size
const Layout = lazy(() => import('./components/Layout'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Repositories = lazy(() => import('./pages/Repositories'));
const GitHubRepoInput = lazy(() => import('./pages/GitHubRepoInput'));
const AddRepositoryOptions = lazy(() => import('./pages/AddRepositoryOptions'));
const AddExternalMcpServer = lazy(() => import('./pages/AddExternalMcpServer'));
const ReviewRepository = lazy(() => import('./pages/ReviewRepository'));
const ConfigPage = lazy(() => import('./pages/ConfigPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
// const McpContainers = lazy(() => import('./pages/McpContainers')); // Remove import
const DeployContainerPage = lazy(() => import('./pages/DeployContainerPage'));
const NotFound = lazy(() => import('./pages/NotFound'));

function App() {
  return (
    <Suspense fallback={<div class="p-4">Loading...</div>}>
      <Layout>
        <Router>
          <Route path="/" component={Dashboard} />
          <Route path="/repositories" component={Repositories} />
          {/* <Route path="/mcp-containers" component={McpContainers} /> */}{/* Remove route */}
          <Route path="/deploy-container/:repoName" component={DeployContainerPage} />
          <Route path="/add-github-repo" component={GitHubRepoInput} />
          <Route path="/add-repository-options" component={AddRepositoryOptions} />
          <Route path="/add-external-mcp-server" component={AddExternalMcpServer} />
          <Route path="/review-repository" component={ReviewRepository} />
          <Route path="/config" component={ConfigPage} />
          <Route path="/settings" component={SettingsPage} />
          <Route path="*" component={NotFound} />
        </Router>
      </Layout>
    </Suspense>
  );
}

export default App; 