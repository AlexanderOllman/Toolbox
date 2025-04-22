import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Repositories from './pages/Repositories';
import GitHubRepoInput from './pages/GitHubRepoInput';
import ReviewRepository from './pages/ReviewRepository';
import ConfigPage from './pages/ConfigPage';
import VectorSettings from './pages/VectorSettings';
import NotFound from './pages/NotFound';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repositories" element={<Repositories />} />
        <Route path="/add-github-repo" element={<GitHubRepoInput />} />
        <Route path="/review-repository" element={<ReviewRepository />} />
        <Route path="/config" element={<ConfigPage />} />
        <Route path="/vector-settings" element={<VectorSettings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export default App; 