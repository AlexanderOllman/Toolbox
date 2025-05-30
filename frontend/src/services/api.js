import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
  withCredentials: false,
  maxRedirects: 5,
});

api.interceptors.request.use(
  config => {
    if (!config.url.endsWith('/') && !config.url.includes('.')) {
      config.url = `${config.url}/`;
    }
    console.log(`Outgoing request: ${config.method.toUpperCase()} ${config.baseURL}${config.url}`);
    return config;
  },
  error => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  response => {
    console.log(`Response (${response.status}): ${response.config.method.toUpperCase()} ${response.config.url}`);
    return response;
  },
  error => {
    if (error.response) {
      console.error(`Error response (${error.response.status}): ${error.config.method.toUpperCase()} ${error.config.url}`);
    } else if (error.request) {
      console.error(`No response received: ${error.config?.method?.toUpperCase()} ${error.config?.url}`);
    } else {
      console.error('Error setting up request:', error.message);
    }
    return Promise.reject(error);
  }
);

// Repository API
export const getRepositories = async () => {
  const response = await api.get('/repositories');
  return response.data;
};

export const getRepository = async (name) => {
  const response = await api.get(`/repositories/${name}`);
  return response.data;
};

export const createRepository = async (data) => {
  const response = await api.post('/repositories', data);
  return response.data;
};

export const deleteRepository = async (name) => {
  await api.delete(`/repositories/${name}`);
  return true;
};

export const fetchRepositoryDetails = async (repoUrl) => {
  try {
    const response = await api.post('/repositories/details', { repo_url: repoUrl });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const searchRepositories = async (query, limit = 5) => {
  try {
    const response = await api.post('/repositories/search', { query, limit });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Configuration API
export const getYamlConfig = async () => {
  const response = await api.get('/config/yaml');
  return response.data;
};

export const getJsonConfig = async () => {
  const response = await api.get('/config/json');
  return response.data;
};

export const generateConfigFile = async (outputPath = null) => {
  const params = outputPath ? { output_path: outputPath } : {};
  const response = await api.post('/config/generate', params);
  return response.data;
};

export const downloadConfigFile = () => {
  window.location.href = '/api/config/download';
};

// Vector Database Settings API
export const getSettings = async () => {
  const response = await api.get('/config/settings');
  return response.data;
};

export const updateSettings = async (items) => {
  const response = await api.post('/config/settings', { items });
  return response.data;
};

export const testQdrantConnection = async () => {
  const response = await api.get('/config/test-qdrant');
  return response.data;
};

export const getQdrantStatus = async () => {
  const response = await api.get('/config/qdrant-status');
  return response.data;
};

export default api;