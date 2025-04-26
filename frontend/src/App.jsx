import { Router, Route } from 'preact-router';
import { lazy, Suspense } from 'preact/compat';

// Use lazy loading for components to reduce initial bundle size
const Layout = lazy(() => import('./components/Layout'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Repositories = lazy(() => import('./pages/Repositories'));
const GitHubRepoInput = lazy(() => import('./pages/GitHubRepoInput'));
const ReviewRepository = lazy(() => import('./pages/ReviewRepository'));
const ConfigPage = lazy(() => import('./pages/ConfigPage'));
const VectorSettings = lazy(() => import('./pages/VectorSettings'));
const NotFound = lazy(() => import('./pages/NotFound'));

function App() {
  return (
    <Suspense fallback={<div class="p-4">Loading...</div>}>
      <Layout>
        <Router>
          <Route path="/" component={Dashboard} />
          <Route path="/repositories" component={Repositories} />
          <Route path="/add-github-repo" component={GitHubRepoInput} />
          <Route path="/review-repository" component={ReviewRepository} />
          <Route path="/config" component={ConfigPage} />
          <Route path="/vector-settings" component={VectorSettings} />
          <Route path="*" component={NotFound} />
        </Router>
      </Layout>
    </Suspense>
  );
}

export default App; 