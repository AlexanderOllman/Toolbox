import { useState, useEffect } from 'preact/hooks';
import { createRepository, checkPortAvailability, fetchRepositoryDetails, getRepository, updateRepository, getSettings } from '../services/api';
import Modal from '../components/Modal';

export default function ReviewRepository() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isEditMode, setIsEditMode] = useState(false);
  const [repoNameToEdit, setRepoNameToEdit] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    repo_url: '', // For Git repos, or external://<serverName> for external
    description: '',
    command: '',
    args: [],
    env: [], // This will now be an array of {key, value, status, included}
    has_dockerfile: false,
    deploy_as_container: false,
    container_args_user: [],
    is_external_config: false, // New field
    transport: 'http', // New field - default for external
    url: '', // New field - URL for external server
    headers: [], // New field - array of {key, value} for external server
    read_transport_sse_timeout_seconds: '', // New field - optional timeout for SSE
    has_docker_compose: false, // Populate from details
  });
  const [newArg, setNewArg] = useState('');
  const [newEnvKey, setNewEnvKey] = useState('');
  const [newEnvValue, setNewEnvValue] = useState('');
  const [newHeaderKey, setNewHeaderKey] = useState(''); // New state for external headers
  const [newHeaderValue, setNewHeaderValue] = useState(''); // New state for external headers
  // New state for container arg inputs
  const [newContainerArgKey, setNewContainerArgKey] = useState('');
  const [newContainerArgValue, setNewContainerArgValue] = useState('');

  // State for suggested host port for Docker deployment
  const [suggestedHostPort, setSuggestedHostPort] = useState('');
  const [suggestedHostPortStatus, setSuggestedHostPortStatus] = useState(''); // e.g., 'checking', 'available', 'unavailable', 'error'
  const [suggestedHostPortMessage, setSuggestedHostPortMessage] = useState('');
  const MCP_CONTAINER_PORT = 8000; // Define the target container port

  const [openAIKey, setOpenAIKey] = useState(null);
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);

  // Load details from URL query parameters
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const repoNameFromQuery = urlParams.get('repo_name'); // For edit mode
    const stateParam = urlParams.get('state'); // For add new from GitHubRepoInput
    
    const populateFormData = (details, repoUrlForContext) => {
      let initialEnv = [];
      if (details.env && typeof details.env === 'object' && !details.is_external_config) { // Only process for non-external
        initialEnv = Object.entries(details.env).map(([key, envDetail]) => {
          const isMandatory = envDetail.status === 'Mandatory';
          return {
            key: key,
            value: envDetail.value || '',
            status: envDetail.status || 'Optional',
            included: envDetail.status === 'Mandatory' || (envDetail.status === 'Optional' && !!envDetail.value),
          };
        });
      }

      let initialContainerArgs = [];
      if (details.container_args_template && typeof details.container_args_template === 'object') {
        initialContainerArgs = Object.entries(details.container_args_template)
                                   .map(([key, value]) => ({ key, value: value || "" }));
      }
      
      if (details.container_args_user && typeof details.container_args_user === 'object' && Object.keys(details.container_args_user).length > 0) {
        initialContainerArgs = Object.entries(details.container_args_user)
                                      .map(([key, value]) => ({ key, value: value || "" }));
      }

      let initialHeaders = [];
      if (details.is_external_config && details.headers) {
        try {
          const parsedHeaders = typeof details.headers === 'string' ? JSON.parse(details.headers) : details.headers;
          if (typeof parsedHeaders === 'object' && parsedHeaders !== null) {
            initialHeaders = Object.entries(parsedHeaders).map(([key, value]) => ({ key, value }));
          } else {
            // Handle case where headers might be an array of objects if already in desired format
            if (Array.isArray(parsedHeaders)) initialHeaders = parsedHeaders;
          }
        } catch (e) {
          console.error("Error parsing headers for external config:", e);
          // Keep initialHeaders as empty array or handle error appropriately
        }
      }


      setFormData({
        name: details.name || '',
        repo_url: details.is_external_config ? `external://${details.name}` : (details.repo_url || repoUrlForContext || ''),
        description: details.description || '',
        command: details.is_external_config ? '' : (details.command || ''),
        args: details.is_external_config ? [] : (details.args || []),
        env: details.is_external_config ? [] : initialEnv,
        has_dockerfile: details.is_external_config ? false : (details.has_dockerfile || false),
        deploy_as_container: details.is_external_config ? false : (details.deploy_as_container || false),
        container_args_user: details.is_external_config ? [] : initialContainerArgs,
        is_external_config: details.is_external_config || false,
        transport: details.is_external_config ? (details.transport || 'http') : 'http',
        url: details.is_external_config ? (details.url || '') : '',
        headers: initialHeaders, // Parsed headers
        read_transport_sse_timeout_seconds: details.is_external_config ? (details.read_transport_sse_timeout_seconds || '') : '',
        has_docker_compose: details.has_docker_compose || false, // Populate from details
      });

      if (details.has_dockerfile && !details.is_external_config) {
        let portToCheck = 8001; // Default candidate
        // If editing, check if a port is already set in container_args_user
        const existingPortArg = initialContainerArgs.find(arg => arg.key === '-p');
        if (existingPortArg && existingPortArg.value) {
            const portMapping = existingPortArg.value.split(':');
            if (portMapping.length === 2 && !isNaN(parseInt(portMapping[0]))) {
                portToCheck = parseInt(portMapping[0]);
            }
        }
        
        const checkPort = async (hostPort) => {
          setSuggestedHostPort(String(hostPort));
          setSuggestedHostPortStatus('checking');
          setSuggestedHostPortMessage(`Checking availability of host port ${hostPort}...`);
          try {
            const result = await checkPortAvailability(hostPort);
            setSuggestedHostPortStatus(result.status);
            setSuggestedHostPortMessage(result.message);
          } catch (err) {
            console.error(`Failed to check host port ${hostPort}:`, err);
            setSuggestedHostPortStatus('error');
            setSuggestedHostPortMessage(`Failed to check port ${hostPort}: ${err.response?.data?.detail || err.message}`);
          }
        };
        checkPort(portToCheck);
      }
      setLoading(false);
    };
    
    const fetchAndSetRepoDetailsForEdit = async (repoName) => {
      setLoading(true);
      setError(null);
      try {
        const fetchedDetails = await getRepository(repoName); // Use the service function
        if (fetchedDetails) {
          populateFormData(fetchedDetails, fetchedDetails.repo_url); // Pass repo_url from fetched data
          // Set edit mode specific states AFTER successful fetch and populate
          setIsEditMode(true);
          setRepoNameToEdit(repoName);
        } else {
          setError('Repository details not found for editing.');
          // Redirect or show a clear message
          window.location.href = '/repositories'; 
        }
      } catch (err) {
        console.error('Error fetching repository details for edit:', err);
        setError(err.response?.data?.detail || 'Failed to fetch repository details for editing.');
        // Redirect or show a clear message
         window.location.href = '/repositories';
      } finally {
        setLoading(false);
      }
    };

    const fetchDetailsAndPopulateForAdd = async (url) => { // Renamed from fetchDetailsAndPopulate
      setLoading(true);
      setError(null);
      try {
        // Use the existing fetchRepositoryDetails function
        const fetchedDetails = await fetchRepositoryDetails(url); // Changed from fetchRepositoryDetailsPost
        if (fetchedDetails) {
          populateFormData(fetchedDetails, url);
        } else {
          setError('Repository details not found.');
          setLoading(false);
          // Optionally redirect if details are mandatory for this page
          // window.location.href = '/add-github-repo'; 
        }
      } catch (err) {
        console.error('Error fetching repository details:', err);
        setError(err.response?.data?.detail || 'Failed to fetch repository details.');
        setLoading(false);
        // Optionally redirect
        // window.location.href = '/add-github-repo';
      }
    };

    const fetchInitialSettings = async () => {
      try {
        const currentSettings = await getSettings();
        setOpenAIKey(currentSettings.OPENAI_API_KEY || '');
      } catch (err) {
        console.error("Failed to fetch settings for ReviewRepository:", err);
        // Decide if this is a critical error for this page
      }
    };

    fetchInitialSettings(); // Call to fetch settings

    if (repoNameFromQuery) {
      // EDIT MODE: fetch by repo_name
      fetchAndSetRepoDetailsForEdit(decodeURIComponent(repoNameFromQuery));
    } else if (stateParam) {
      // ADD NEW flow: details are in the 'state' query parameter
      setLoading(true); 
      try {
        const state = JSON.parse(decodeURIComponent(stateParam));
        if (state.details && state.repoUrl) {
          // For "add new", the details from state (GPT scan) are used to prefill.
          // The populateFormData function will set loading to false.
          populateFormData(state.details, state.repoUrl);
        } else {
          setError("Invalid state data provided.");
          setLoading(false);
          window.location.href = '/add-github-repo';
        }
      } catch (e) {
        console.error('Error parsing state parameter:', e);
        setError("Failed to parse initial data.");
        setLoading(false);
        window.location.href = '/add-github-repo';
      }
    } else {
      // No repo_url and no state parameter, redirect
      setLoading(false); // Ensure loading is false before redirect
      window.location.href = '/add-github-repo';
    }
  }, []);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      // Handle checkbox toggle for deploy_as_container
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleEnvChange = (index, field, value) => {
    setFormData((prev) => {
      const updatedEnv = [...prev.env];
      updatedEnv[index] = { ...updatedEnv[index], [field]: value };
      return { ...prev, env: updatedEnv };
    });
  };

  const handleAddArg = () => {
    if (newArg.trim()) {
      setFormData((prev) => ({
        ...prev,
        args: [...prev.args, newArg.trim()],
      }));
      setNewArg('');
    }
  };

  const handleRemoveArg = (index) => {
    setFormData((prev) => ({
      ...prev,
      args: prev.args.filter((_, i) => i !== index),
    }));
  };

  const handleAddEnv = () => {
    if (newEnvKey.trim()) {
      setFormData((prev) => ({
        ...prev,
        env: [...prev.env, { key: newEnvKey.trim(), value: newEnvValue.trim(), status: 'Optional', included: true }],
      }));
      setNewEnvKey('');
      setNewEnvValue('');
    }
  };

  const handleRemoveEnv = (index) => {
    setFormData((prev) => ({
      ...prev,
      env: prev.env.filter((_, i) => i !== index),
    }));
  };

  // --- Handlers for External Server Headers ---
  const handleHeaderChange = (index, field, value) => {
    setFormData((prev) => {
      const updatedHeaders = [...prev.headers];
      updatedHeaders[index] = { ...updatedHeaders[index], [field]: value };
      return { ...prev, headers: updatedHeaders };
    });
  };

  const handleAddHeader = () => {
    if (newHeaderKey.trim()) {
      setFormData((prev) => ({
        ...prev,
        headers: [...prev.headers, { key: newHeaderKey.trim(), value: newHeaderValue.trim() }],
      }));
      setNewHeaderKey('');
      setNewHeaderValue('');
    }
  };

  const handleRemoveHeader = (index) => {
    setFormData((prev) => ({
      ...prev,
      headers: prev.headers.filter((_, i) => i !== index),
    }));
  };

  // --- New handlers for Container Arguments ---
  const handleContainerArgChange = (index, field, value) => {
    setFormData((prev) => {
      const updatedArgs = [...prev.container_args_user];
      updatedArgs[index] = { ...updatedArgs[index], [field]: value };
      return { ...prev, container_args_user: updatedArgs };
    });
  };
  
  const handleAddContainerArg = () => {
    if (newContainerArgKey.trim()) {
      setFormData((prev) => ({
        ...prev,
        container_args_user: [...prev.container_args_user, { key: newContainerArgKey.trim(), value: newContainerArgValue.trim() }],
      }));
      setNewContainerArgKey('');
      setNewContainerArgValue('');
    }
  };

  const handleRemoveContainerArg = (index) => {
    setFormData((prev) => ({
      ...prev,
      container_args_user: prev.container_args_user.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Basic validation rules (can be expanded)
    if (formData.is_external_config) {
      if (!formData.name || !formData.description || !formData.url) {
        setError("For external configurations, Name, Description, and URL are required.");
        setLoading(false);
        return;
      }
      // ... other external config validations
    } else { // Non-external: Git repo for container or local command
      if (!formData.name) {
        setError("Repository Name is required.");
        setLoading(false);
        return;
      }
      // If not deploying as container (and not compose), command is required
      if (!formData.deploy_as_container && !formData.has_docker_compose && !formData.command) {
        setError("Command is required for non-containerized execution.");
        setLoading(false);
        return;
      }
      // URL required if not compose and no dockerfile (implies git repo for local command execution)
      if (!formData.has_docker_compose && !formData.has_dockerfile && !formData.repo_url) {
        setError("Repository URL is required if not using Dockerfile or Docker Compose.");
        setLoading(false);
        return;
      }
    }

    // If NOT an external config, and it's a new repository (not edit mode)
    // and user has chosen to deploy as a container, navigate to deployment config page.
    if (!isEditMode && !formData.is_external_config && formData.deploy_as_container) {
      const deploymentConfigState = { ...formData }; 
      try {
        const stateParam = encodeURIComponent(JSON.stringify(deploymentConfigState));
        window.location.href = `/deploy-container/${encodeURIComponent(formData.name)}?initialState=${stateParam}`;
        setLoading(false);
        return; // Stop further execution in handleSubmit
      } catch (routingError) {
        console.error("Routing error:", routingError);
        setError("Failed to navigate to deployment configuration page.");
        setLoading(false);
        return;
      }
    }

    // Original handleSubmit logic for external configs or EDITING existing repositories
    // (as these are already in DB or are managed differently)
    let payload;
    if (formData.is_external_config) {
      const headersObject = formData.headers.reduce((obj, item) => {
        if (item.key) obj[item.key] = item.value;
        return obj;
      }, {});

      payload = {
        name: formData.name,
        description: formData.description,
        repo_url: `external://${formData.name}`, // Convention for external
        is_external_config: true,
        transport: formData.transport,
        url: formData.url,
        headers: JSON.stringify(headersObject),
        read_transport_sse_timeout_seconds: formData.read_transport_sse_timeout_seconds ? parseInt(formData.read_transport_sse_timeout_seconds, 10) : null,
        // Fields not applicable to external that need to be explicitly nulled or defaulted if schema requires
        command: '', // Or null depending on backend schema for external
        args: [],
        env: {}, // External env vars are not typically managed this way
        has_dockerfile: false,
        deploy_as_container: false,
        container_args_user: {},
        // container_args_template: {}, // This is usually derived, not sent
        deployment_status: 'n/a_external', // Backend sets this too
        has_docker_compose: formData.has_docker_compose, // Pass this through
      };
    } else if (formData.deploy_as_container) {
      // Handle Docker deployment payload
      const finalEnv = formData.env
        .filter(ev => ev.included) // Only included env vars
        .reduce((obj, item) => {
          if (item.key) obj[item.key] = { value: item.value, status: item.status || 'Optional' };
          return obj;
        }, {});

      // Transform container_args_user from array of {key, value} to object
      const finalContainerArgsUser = formData.container_args_user.reduce((obj, item) => {
        if (item.key) obj[item.key] = item.value;
        return obj;
      }, {});
      
      // If suggestedHostPort is set and valid, ensure it's included in container_args_user as -p
      if (suggestedHostPort && !isNaN(parseInt(suggestedHostPort))) {
        // Avoid duplicate -p mapping if user already added one for MCP_CONTAINER_PORT
        let mcpPortMapped = false;
        for (const key in finalContainerArgsUser) {
            if ((key === '-p' || key === '--publish') && finalContainerArgsUser[key].includes(`:${MCP_CONTAINER_PORT}`)) {
                mcpPortMapped = true;
                break;
            }
        }
        if (!mcpPortMapped) {
            finalContainerArgsUser['-p'] = `${suggestedHostPort}:${MCP_CONTAINER_PORT}`;
        }
      }


      payload = {
        name: formData.name,
        repo_url: formData.repo_url,
        description: formData.description,
        command: formData.command,
        args: formData.args || [],
        env: finalEnv,
        has_dockerfile: formData.has_dockerfile,
        deploy_as_container: true,
        container_args_user: finalContainerArgsUser, // Send as object
        // container_args_template: {}, // This is derived by backend usually
        is_external_config: false,
        transport: 'stdio', // Default for non-external
        url: '',
        headers: '{}',
        read_transport_sse_timeout_seconds: null,
        deployment_status: 'not_deployed', // Initial status for new container repo
        has_docker_compose: formData.has_docker_compose, // Pass this through
      };
    } else {
      // Standard Git repository payload
      const finalEnv = formData.env
        .filter(ev => ev.included)
        .reduce((obj, item) => {
          if (item.key) obj[item.key] = { value: item.value, status: item.status || 'Optional' };
          return obj;
        }, {});

      payload = {
        name: formData.name,
        repo_url: formData.repo_url,
        description: formData.description,
        command: formData.command,
        args: formData.args,
        env: finalEnv,
        has_dockerfile: formData.has_dockerfile, // Retain this info
        deploy_as_container: false,
        container_args_user: {}, // Clear for non-container
        // container_args_template: {}, // Clear for non-container
        is_external_config: false,
        transport: 'stdio',
        url: '',
        headers: '{}',
        read_transport_sse_timeout_seconds: null,
        deployment_status: 'not_deployed', // Initial status for new git repo
        has_docker_compose: formData.has_docker_compose, // Pass this through
      };
    }

    try {
      let savedRepo;
      if (isEditMode && repoNameToEdit) {
        console.log("Updating repository:", repoNameToEdit, payload);
        savedRepo = await updateRepository(repoNameToEdit, payload); // Use updateRepository
        alert('Repository updated successfully!');
      } else {
        console.log("Creating repository with payload:", payload);
        savedRepo = await createRepository(payload);
        alert('Repository created successfully!');
      }
      
      // Redirect logic for external configs or after editing
      if (formData.is_external_config || isEditMode) {
          window.location.href = '/repositories';
      } else if (formData.deploy_as_container && savedRepo && savedRepo.name) {
        // This case should now be handled by the navigation to DeployContainerPage for NEW container repos
        // If it's an EDIT of a container repo, it might still come here, then redirect to /repositories.
        // For clarity, let's assume new container deployments are routed above.
        // If we reached here for a container, it implies an edit, so /repositories is fine.
        window.location.href = '/repositories'; 
      } else {
        window.location.href = '/repositories';
      }

    } catch (err) {
      console.error("Error saving repository:", err);
      // More specific error handling based on err.response.data if available
      let errorMessage = 'Failed to save repository.';
      if (err.response && err.response.data && err.response.data.detail) {
        if (typeof err.response.data.detail === 'string') {
          errorMessage = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail) && err.response.data.detail.length > 0) {
          // Handle FastAPI validation errors which are arrays of objects
          errorMessage = err.response.data.detail.map(d => `${d.loc.join(' -> ')}: ${d.msg}`).join('; ');
        } else if (typeof err.response.data.detail === 'object') {
          // Handle other object-based error details
          errorMessage = JSON.stringify(err.response.data.detail);
        }
      } else if (err.message) {
        errorMessage = err.message;
      }
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !isEditMode && !new URLSearchParams(window.location.search).get('repo_name')) { // Show full page loader only for initial add flow before form is ready
    return <div class="flex justify-center items-center h-screen"><div class="loader"></div><div>Loading Repository Details...</div></div>;
  }
  
  if (!isEditMode && error && !new URLSearchParams(window.location.search).get('repo_name')) { // If error during initial load for add.
      return <div class="text-red-500 text-center p-4">Error: {error}. Please try <a href="/add-github-repo" class="text-blue-500 hover:underline">adding the repository again</a>.</div>;
  }

  // Specific loader for edit mode while fetching details
  if (isEditMode && loading) {
    return <div class="flex justify-center items-center h-screen"><div class="loader"></div><div>Loading Repository Details for Edit...</div></div>;
  }
  // Specific error for edit mode if fetching details failed
  if (isEditMode && error && !formData.name) { // If error during initial load for edit.
    return <div class="text-red-500 text-center p-4">Error: {error}. Could not load repository. Please return to <a href="/repositories" class="text-blue-500 hover:underline">Repositories page</a>.</div>;
  }

  return (
    <div class="container mx-auto p-4 max-w-2xl">
      <Modal 
        isOpen={isApiKeyModalOpen} 
        onClose={() => setIsApiKeyModalOpen(false)} 
        title="OpenAI API Key Required"
      >
        <p>
          An OpenAI API Key is required to properly process and add new repositories, including generating necessary data from descriptions.
        </p>
        <p class="mt-2">
          Please configure your OpenAI API Key in the settings before adding a new repository.
        </p>
        <div class="mt-4 flex justify-end space-x-2">
          <button 
            type="button"
            onClick={() => setIsApiKeyModalOpen(false)} 
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500"
          >
            Cancel
          </button>
          <button 
            type="button"
            onClick={() => {
              setIsApiKeyModalOpen(false);
              window.location.href = '/settings'; // Use window.location.href for simplicity here, or preact-router's route
            }} 
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Go to Settings
          </button>
          </div>
      </Modal>
      <h1 class="text-2xl font-bold mb-6 text-center">{isEditMode ? 'Edit Repository' : 'Review and Add Repository'}</h1>
      {error && <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-4" role="alert">
        <strong class="font-bold">Error: </strong>
        <span class="block sm:inline">{error}</span>
      </div>}
      <form onSubmit={handleSubmit} class="space-y-6 bg-white shadow-md rounded px-8 pt-6 pb-8 mb-4">
        
        <div>
          <label htmlFor="name" class="block text-sm font-medium text-gray-700">Repository Name / Server Name</label>
                    <input
                      type="text"
                      name="name"
                      id="name"
                      value={formData.name}
                      onChange={handleChange}
            required
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            // Make name readonly if it's an external config being edited, as repo_url depends on it.
            // Or, if we allow changing it, we must update repo_url accordingly and ensure uniqueness.
            // For now, let's make it readonly for external edit to simplify.
            // The name for external configs is derived from the URL path `external://<name>`
            // and it is the primary key, so it cannot be changed once created.
            readOnly={isEditMode && formData.is_external_config}
            disabled={isEditMode && formData.is_external_config}
          />
           {isEditMode && formData.is_external_config && <p class="text-xs text-gray-500 mt-1">Server Name cannot be changed for existing external configurations.</p>}
                </div>

        <div>
          <label htmlFor="description" class="block text-sm font-medium text-gray-700">Description</label>
                    <textarea
            name="description"
                      id="description"
                      value={formData.description}
                      onChange={handleChange}
            rows="3"
            class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
          ></textarea>
        </div>

        {/* Conditional Fields for External MCP Server Configuration */}
        {formData.is_external_config ? (
          <>
            <div>
              <label htmlFor="repo_url_external_identifier" class="block text-sm font-medium text-gray-700">Internal Identifier</label>
              <input
                type="text"
                name="repo_url_external_identifier" // Changed name to avoid conflict if any, though not strictly necessary for readonly
                id="repo_url_external_identifier"
                value={formData.repo_url} // Still bound to formData.repo_url
                readOnly
                disabled
                class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm bg-gray-100"
              />
              <p class="text-xs text-gray-500 mt-1">This internal identifier cannot be changed.</p>
            </div>

            <div>
              <label htmlFor="transport" class="block text-sm font-medium text-gray-700">Transport Protocol</label>
              <select
                name="transport"
                id="transport"
                value={formData.transport}
                onChange={handleChange}
                required
                class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              >
                <option value="stdio">stdio</option>
                <option value="sse">sse</option>
                <option value="http">http</option>
                <option value="streamable_http">streamable_http</option>
              </select>
            </div>

            <div>
              <label htmlFor="url" class="block text-sm font-medium text-gray-700">Server URL</label>
              <input
                type="url"
                name="url"
                id="url"
                value={formData.url}
                onChange={handleChange}
                placeholder="e.g., http://localhost:8000/mcp"
                required
                class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                    />
                  </div>
            
            {formData.transport === 'sse' && (
                 <div>
                 <label htmlFor="read_transport_sse_timeout_seconds" class="block text-sm font-medium text-gray-700">SSE Timeout (seconds, optional)</label>
                 <input
                   type="number"
                   name="read_transport_sse_timeout_seconds"
                   id="read_transport_sse_timeout_seconds"
                   value={formData.read_transport_sse_timeout_seconds}
                   onChange={handleChange}
                   placeholder="e.g., 300"
                   class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                 />
                </div>
            )}

            {/* Headers Management for External Config */}
            <div class="space-y-2">
                <h3 class="text-sm font-medium text-gray-700">Headers</h3>
                {formData.headers.map((header, index) => (
                  <div key={index} class="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="Key"
                      value={header.key}
                      onChange={(e) => handleHeaderChange(index, 'key', e.target.value)}
                      class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Value"
                      value={header.value}
                      onChange={(e) => handleHeaderChange(index, 'value', e.target.value)}
                      class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                    />
                    <button type="button" onClick={() => handleRemoveHeader(index)} class="text-red-500 hover:text-red-700">&times;</button>
                      </div>
                    ))}
                <div class="flex items-center space-x-2">
                  <input
                    type="text"
                    placeholder="New Header Key"
                    value={newHeaderKey}
                    onChange={(e) => setNewHeaderKey(e.target.value)}
                    class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                  />
                  <input
                    type="text"
                    placeholder="New Header Value"
                    value={newHeaderValue}
                    onChange={(e) => setNewHeaderValue(e.target.value)}
                    class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                  />
                  <button type="button" onClick={handleAddHeader} class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm">Add Header</button>
                </div>
                  </div>

          </>
        ) : (
          <> {/* Fields for Git/Container Repositories */}
            <div>
              <label htmlFor="repo_url" class="block text-sm font-medium text-gray-700">Repository URL</label>
              <input
                type="url"
                name="repo_url"
                id="repo_url"
                value={formData.repo_url}
                onChange={handleChange}
                readOnly={isEditMode || formData.has_dockerfile}
                disabled={isEditMode || formData.has_dockerfile}
                required={!formData.is_external_config && !formData.has_docker_compose}
                class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm bg-gray-50"
              />
              {(isEditMode || formData.has_dockerfile) && <p class="text-xs text-gray-500 mt-1">Repository URL cannot be changed after initial setup.</p>}
              {formData.has_docker_compose && <p class="text-xs text-green-600 mt-1">Docker Compose file detected. Deployment will use docker-compose.yml.</p>}
            </div>

            {/* Checkbox for Docker Deployment */}
            {formData.has_dockerfile && !formData.has_docker_compose && (
              <div class="mt-4">
                <label class="flex items-center">
                        <input
                    type="checkbox"
                          name="deploy_as_container"
                          checked={formData.deploy_as_container}
                          onChange={handleChange}
                    class="h-4 w-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                        />
                  <span class="ml-2 text-sm text-gray-700">Deploy as Container</span>
                        </label>
                      </div>
            )}

            {/* Fields for Container Deployment (Only if deploy_as_container is true) */}
            {formData.deploy_as_container && formData.has_dockerfile && (
            <>
                {/* Suggested Host Port Section */}
                <div class="my-4 p-3 bg-gray-50 rounded border border-gray-200">
                    <p class="text-sm font-medium text-gray-700">Host Port Mapping (for container port {MCP_CONTAINER_PORT})</p>
                    <div class="flex items-center space-x-2 mt-1">
                        <input
                            type="text"
                            placeholder="Host Port"
                            value={suggestedHostPort}
                            onChange={(e) => {
                                setSuggestedHostPort(e.target.value);
                                // Find the -p argument and update it or add it
                                const portArgIndex = formData.container_args_user.findIndex(arg => arg.key === '-p');
                                const portValue = e.target.value ? `${e.target.value}:${MCP_CONTAINER_PORT}` : "";
                                
                                if (portArgIndex > -1) {
                                    handleContainerArgChange(portArgIndex, 'value', portValue);
                                } else if (e.target.value) { // Add new -p arg only if there's a value
                                     setFormData(prev => ({
                                        ...prev,
                                        container_args_user: [...prev.container_args_user, {key: '-p', value: portValue}]
                                    }));
                                }
                            }}
                            class="w-1/3 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                        />
                        <button 
                            type="button" 
                            onClick={async () => {
                                if (!suggestedHostPort) {
                                    setSuggestedHostPortStatus('error');
                                    setSuggestedHostPortMessage('Please enter a host port to check.');
                                    return;
                                }
                                setSuggestedHostPortStatus('checking');
                                setSuggestedHostPortMessage(`Checking port ${suggestedHostPort}...`);
                                try {
                                    const result = await checkPortAvailability(parseInt(suggestedHostPort, 10));
                                    setSuggestedHostPortStatus(result.status);
                                    setSuggestedHostPortMessage(result.message);
                                } catch (err) {
                                    setSuggestedHostPortStatus('error');
                                    setSuggestedHostPortMessage(err.response?.data?.detail || 'Error checking port.');
                                }
                            }}
                            disabled={suggestedHostPortStatus === 'checking'}
                            class="px-3 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 text-sm disabled:opacity-50"
                        >
                            Check Port
                        </button>
                    </div>
                    {suggestedHostPortMessage && (
                        <p className={`text-xs mt-1 ${
                            suggestedHostPortStatus === 'available' ? 'text-green-600' :
                            suggestedHostPortStatus === 'unavailable' ? 'text-red-600' :
                            suggestedHostPortStatus === 'error' ? 'text-red-600' :
                            'text-gray-500'
                        }`}>
                            {suggestedHostPortMessage}
                        </p>
                    )}
                    <p class="text-xs text-gray-500 mt-1">
                        This will add/update the <code>-p {suggestedHostPort || '<host_port>'}:{MCP_CONTAINER_PORT}</code> argument.
                        You can manage other Docker arguments below.
                    </p>
                  </div>

                
                {/* Container Arguments Management */}
                <div class="space-y-2">
                <h3 class="text-sm font-medium text-gray-700">Container Arguments (Docker run options)</h3>
                          {formData.container_args_user.map((arg, index) => (
                    // Do not display the -p argument here if it's managed by suggestedHostPort input
                    arg.key === '-p' && suggestedHostPort ? null : (
                    <div key={index} class="flex items-center space-x-2">
                                  <input 
                                      type="text" 
                        placeholder="Key (e.g., -v)"
                                      value={arg.key} 
                                      onChange={(e) => handleContainerArgChange(index, 'key', e.target.value)}
                        class="w-1/3 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                                  />
                                  <input 
                                      type="text" 
                        placeholder="Value (e.g., /host/path:/container/path)"
                                      value={arg.value} 
                                      onChange={(e) => handleContainerArgChange(index, 'value', e.target.value)}
                        class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                                  />
                    <button type="button" onClick={() => handleRemoveContainerArg(index)} class="text-red-500 hover:text-red-700">&times;</button>
                    </div>
                    )
                          ))}
                        <div class="flex items-center space-x-2">
                            <input 
                                type="text" 
                    placeholder="New Arg Key"
                                value={newContainerArgKey} 
                                onChange={(e) => setNewContainerArgKey(e.target.value)} 
                    class="w-1/3 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                            />
                            <input 
                                type="text" 
                    placeholder="New Arg Value"
                                value={newContainerArgValue} 
                                onChange={(e) => setNewContainerArgValue(e.target.value)} 
                    class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                            />
                    <button type="button" onClick={handleAddContainerArg} class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm">Add Argument</button>
                      </div>
                    </div>
            </>
                )}

            {/* Fields for Local Execution (Only if NOT deploy_as_container OR no Dockerfile) */}
            {(!formData.deploy_as_container || !formData.has_dockerfile) && (
              <>
                <div>
                  <label htmlFor="command" class="block text-sm font-medium text-gray-700">Execution Command</label>
                  <input
                    type="text"
                    name="command"
                    id="command"
                    value={formData.command}
                    onChange={handleChange}
                    placeholder="e.g., python"
                    class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  />
                </div>

                {/* Arguments Management */}
                <div class="space-y-2">
                  <h3 class="text-sm font-medium text-gray-700">Command Arguments</h3>
                  {formData.args.map((arg, index) => (
                    <div key={index} class="flex items-center space-x-2">
                      <input
                        type="text"
                        value={arg}
                        onChange={(e) => {
                          const newArgs = [...formData.args];
                          newArgs[index] = e.target.value;
                          setFormData(prev => ({ ...prev, args: newArgs }));
                        }}
                        class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                      />
                      <button type="button" onClick={() => handleRemoveArg(index)} class="text-red-500 hover:text-red-700">&times;</button>
                    </div>
                  ))}
                  <div class="flex items-center space-x-2">
                                        <input 
                      type="text"
                      placeholder="New Argument"
                      value={newArg}
                      onChange={(e) => setNewArg(e.target.value)}
                      class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                                        />
                    <button type="button" onClick={handleAddArg} class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm">Add Argument</button>
                  </div>
                                </div>
                                
                {/* Environment Variables Management */}
                {/* Simplified Env for now - consider if status/included logic is needed for edit for non-external */}
                <div class="space-y-2">
                  <h3 class="text-sm font-medium text-gray-700">Environment Variables</h3>
                  {formData.env.map((envVar, index) => (
                    <div key={index} class="flex items-center space-x-2">
                        <input
                          type="text"
                                        placeholder="Key"
                                        value={envVar.key} 
                                        onChange={(e) => handleEnvChange(index, 'key', e.target.value)}
                        class="w-1/3 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                        readOnly={envVar.status === 'Mandatory'} // Example: make mandatory keys readonly
                        />
                        <input
                          type="text"
                          placeholder="Value"
                                        value={envVar.value} 
                                        onChange={(e) => handleEnvChange(index, 'value', e.target.value)}
                        class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                      />
                      { envVar.status !== 'Mandatory' && // Allow removing only non-mandatory
                        <button type="button" onClick={() => handleRemoveEnv(index)} class="text-red-500 hover:text-red-700">&times;</button>
                      }
                       {envVar.status && <span class="text-xs text-gray-500">({envVar.status})</span>}
                    </div>
                  ))}
                  <div class="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="New ENV Key"
                      value={newEnvKey}
                      onChange={(e) => setNewEnvKey(e.target.value)}
                      class="w-1/3 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                    />
                    <input
                      type="text"
                      placeholder="New ENV Value"
                      value={newEnvValue}
                      onChange={(e) => setNewEnvValue(e.target.value)}
                      class="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm sm:text-sm"
                    />
                    <button type="button" onClick={handleAddEnv} class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 text-sm">Add ENV Var</button>
                  </div>
                </div>
              </>
            )}
          </>
        )}


        <div class="flex items-center justify-end space-x-3 pt-4">
          <button 
            type="button" 
            onClick={() => window.history.back()}
            class="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
                >
            Cancel
          </button>
                <button
                  type="submit"
            disabled={loading || (formData.deploy_as_container && suggestedHostPortStatus === 'checking')}
            class="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
                >
            {loading ? 'Saving...' : (isEditMode ? 'Save Changes' : 'Add Repository')}
                </button>
        </div>
      </form>
    </div>
  );
} 