import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8020/api';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
  withCredentials: false,
  maxRedirects: 5,
});

apiClient.interceptors.request.use(
  config => {
    console.log(`Outgoing request: ${config.method.toUpperCase()} ${config.baseURL}${config.url}`);
    return config;
  },
  error => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
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
  const response = await apiClient.get('/repositories');
  return response.data;
};

// New function to get container-specific repositories
export const getContainerRepositories = async () => {
  const response = await apiClient.get('/repositories/containers'); // Use the new endpoint
  return response.data;
};

export const getRepository = async (name) => {
  const response = await apiClient.get(`/repositories/${name}`);
  return response.data;
};

export const createRepository = async (data) => {
  const response = await apiClient.post('/repositories', data);
  return response.data;
};

export const updateRepository = async (repoName, data) => {
  const response = await apiClient.put(`/repositories/${repoName}`, data);
  return response.data;
};

// New function to either create or update a repository
export const addOrUpdateRepository = async (repoName, data) => {
  try {
    // Try to get the repository first
    await getRepository(repoName); // If this doesn't throw 404, it exists
    console.log(`Repository ${repoName} found, updating...`);
    return await updateRepository(repoName, data);
  } catch (error) {
    if (error.response && error.response.status === 404) {
      // Not found, so create it
      console.log(`Repository ${repoName} not found, creating...`);
      // Ensure the data payload for creation does not include the repoName in the URL path again
      // The 'data' should be the complete RepositoryCreate model
      return await createRepository(data);
    } else {
      // Other error (not 404), rethrow
      console.error(`Error in addOrUpdateRepository for ${repoName}:`, error);
      throw error;
    }
  }
};

export const deleteRepository = async (name) => {
  await apiClient.delete(`/repositories/${name}`);
  return true;
};

export const fetchRepositoryDetails = async (repoUrl) => {
  try {
    const response = await apiClient.post('/repositories/details', { repo_url: repoUrl });
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const searchRepositories = async (query, limit = 5) => {
  try {
    const response = await apiClient.post('/repositories/search', { query, limit });
    return response.data;
  } catch (error) {
    throw error;
  }
};

// Configuration API
export const getYamlConfig = async () => {
  const response = await apiClient.get('/config/yaml');
  return response.data;
};

export const getJsonConfig = async () => {
  const response = await apiClient.get('/config/json');
  return response.data;
};

export const generateConfigFile = async (outputPath = null) => {
  const params = outputPath ? { output_path: outputPath } : {};
  const response = await apiClient.post('/config/generate', params);
  return response.data;
};

export const downloadConfigFile = () => {
  window.location.href = '/api/config/download';
};

// Vector Database Settings API
export const getSettings = async () => {
  const response = await apiClient.get('/config/settings');
  return response.data;
};

export const updateSettings = async (items) => {
  const payload = { items };
  console.log('Payload being sent to /api/config/settings:', JSON.stringify(payload, null, 2));
  const response = await apiClient.post('/config/settings', payload);
  return response.data;
};

export const getCollectionStatus = async () => {
  const response = await apiClient.get('/config/collection-status');
  return response.data;
};

export const initializeCollections = async () => {
  const response = await apiClient.post('/config/initialize-collections');
  return response.data;
};

export const testQdrantConnection = async () => {
  const response = await apiClient.get('/config/test-qdrant');
  return response.data;
};

export const getQdrantStatus = async () => {
  const response = await apiClient.get('/config/qdrant-status');
  return response.data;
};

// Docker Status API
export const getDockerStatus = async () => {
  const response = await apiClient.get('/config/docker-status');
  return response.data;
};

// New function to get Dockerfile content
export const getDockerfileContent = async (repoName) => {
  try {
    const response = await apiClient.get(`/repositories/${encodeURIComponent(repoName)}/dockerfile`);
    return response.data; // Expecting plain text
  } catch (error) {
    console.error("Error fetching Dockerfile content:", error.response?.data || error.message);
    // Return null or an empty string an error object might be better
    // depending on how the caller handles it.
    if (error.response && error.response.status === 404) {
        return null; // Or specific marker for not found
    }
    throw error.response?.data || new Error("Failed to fetch Dockerfile content.");
  }
};

// New function to deploy a container
export const deployContainer = async (repoName, deployConfig) => {
  console.log(`Deploying ${repoName} with config:`, deployConfig);
  try {
    const response = await apiClient.post(`/repositories/${encodeURIComponent(repoName)}/deploy`, deployConfig, {
      timeout: 300000, // 5 minutes for deployment
    });
    return response.data;
  } catch (error) {
    console.error("Error deploying container:", error.response?.data || error.message);
    throw error.response?.data || new Error("Failed to deploy container.");
  }
};

// New function to check host port availability
export const checkPortAvailability = async (port) => {
  const response = await apiClient.post(`/docker/check-port`, { port });
  return response.data; // Expected: { port: number, status: "available"|"unavailable", message: string }
};

export const finalizeDeployment = async (payload) => {
  console.log("Finalizing deployment with payload:", payload);
  try {
    const response = await apiClient.post('/repositories/finalize-deployment', payload);
    return response.data;
  } catch (error) {
    console.error("Error finalizing deployment:", error.response?.data || error.message);
    throw error.response?.data || new Error("Failed to finalize deployment and save repository.");
  }
};

export default apiClient;