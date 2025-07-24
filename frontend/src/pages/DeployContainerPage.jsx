import { useState, useEffect } from 'preact/hooks';
// import { route } from 'preact-router'; // Not used yet
import { getRepository, getDockerfileContent, deployContainer, checkPortAvailability, finalizeDeployment, addOrUpdateRepository } from '../services/api'; // Added deployContainer and checkPortAvailability

export default function DeployContainerPage(props) {
  const { repoName } = props;
  const [repository, setRepository] = useState(null);
  const [dockerfileContent, setDockerfileContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState(null);
  const [deploySuccess, setDeploySuccess] = useState(null);
  const [deploymentLogs, setDeploymentLogs] = useState(''); // For verbose logs
  
  const [imageName, setImageName] = useState('');
  const [containerArgs, setContainerArgs] = useState([]); // Array of {key, value}
  const [envVars, setEnvVars] = useState([]); // Array of {key, value, status, included}

  // State for new input fields
  const [newContainerArgKey, setNewContainerArgKey] = useState('');
  const [newContainerArgValue, setNewContainerArgValue] = useState('');
  const [newEnvVarKey, setNewEnvVarKey] = useState('');
  const [newEnvVarValue, setNewEnvVarValue] = useState('');
  // For new env vars, status will default to 'Optional', included to true.

  // State for port checking
  const [checkingPort, setCheckingPort] = useState(null); // Stores the port number being checked or null
  // For dedicated port field
  const [dedicatedPortCheckResult, setDedicatedPortCheckResult] = useState(null);
  const [dedicatedPortCheckError, setDedicatedPortCheckError] = useState(null);
  // For generic container arguments port check
  const [genericPortCheckResult, setGenericPortCheckResult] = useState(null);
  const [genericPortCheckError, setGenericPortCheckError] = useState(null);

  // State for dedicated host port
  const [dedicatedHostPort, setDedicatedHostPort] = useState('');
  const [mcpContainerPort, setMcpContainerPort] = useState(8000); // Default, but can be overridden

  // State for attempting local build
  const [attemptLocalBuild, setAttemptLocalBuild] = useState(false);

  // State for attempting to push to registry
  const [attemptPushToRegistry, setAttemptPushToRegistry] = useState(false);

  // New state for deployment stages and detailed status
  const DEPLOYMENT_STAGES = {
    INIT: 'Initializing',
    PULLING_IMAGE: 'Pulling Image',
    BUILDING_IMAGE: 'Building Image',
    PUSHING_IMAGE: 'Pushing Image',
    STARTING_CONTAINER: 'Starting Container',
    VERIFYING_HEALTH: 'Verifying Health',
    DEPLOYED: 'Deployed',
    FAILED: 'Failed'
  };
  const [currentStage, setCurrentStage] = useState(DEPLOYMENT_STAGES.INIT);
  const [stageDetails, setStageDetails] = useState({}); // Stores { stageName: { status: 'pending' | 'success' | 'error', message: '' } }

  // New state for Docker Compose option
  const [useCompose, setUseCompose] = useState(false);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const initialStateParam = urlParams.get('initialState');
    const decodedRepoNameFromProps = decodeURIComponent(repoName); // From props path

    const processRepoData = (repoDataToProcess, source) => {
      console.log(`Processing repo data from ${source}:`, repoDataToProcess);
      setRepository(repoDataToProcess);

      if (repoDataToProcess.has_dockerfile || repoDataToProcess.has_docker_compose) {
        setAttemptLocalBuild(repoDataToProcess.has_dockerfile || false); 
      }

      let derivedImageName = repoDataToProcess.docker_image_name_suggestion || `${repoDataToProcess.name || decodedRepoNameFromProps}:latest`;
      if (!repoDataToProcess.docker_image_name_suggestion && repoDataToProcess.repo_url) {
        const match = repoDataToProcess.repo_url.match(/github\.com[\/:]([^\/]+)\/([^\/.]+)(\.git)?/i);
        if (match) derivedImageName = `${match[1].toLowerCase()}/${match[2].toLowerCase()}:latest`;
      }
      setImageName(derivedImageName);

      if (repoDataToProcess.has_docker_compose) {
        setUseCompose(true);
      }

      // Use suggested port from Dockerfile if available, otherwise default
      const suggestedInternalPort = repoDataToProcess.exposed_port_suggestion;
      if (suggestedInternalPort) {
        setMcpContainerPort(suggestedInternalPort);
        console.log(`Using suggested internal port from Dockerfile: ${suggestedInternalPort}`);
      }

      let prefilledHostPort = '';
      const argsFromSource = Array.isArray(repoDataToProcess.container_args_user) 
        ? repoDataToProcess.container_args_user
        : Object.entries(repoDataToProcess.container_args_user || {}).map(([k, v]) => ({ key: k, value: v || "" }));
      
      setContainerArgs(argsFromSource);

      for (const arg of argsFromSource) {
        if ((arg.key === '-p' || arg.key === '--publish') && typeof arg.value === 'string') {
            if (arg.value.includes(`:${mcpContainerPort}`)) {
          const parts = arg.value.split(':');
                if (parts.length === 2 && parts[1].startsWith(String(mcpContainerPort))) {
            prefilledHostPort = parts[0];
            break;
                } else if (parts.length === 3 && parts[2].startsWith(String(mcpContainerPort))) {
            prefilledHostPort = parts[1];
            break;
                }
          }
        }
      }
      if (prefilledHostPort) {
        setDedicatedHostPort(prefilledHostPort);
      }

      // Environment variables processing
      let combinedEnvVars = [];
      // 1. Process GPT/database ENV vars (repoDataToProcess.env)
      if (Array.isArray(repoDataToProcess.env)) { // From ReviewRepository (array of {key, value, status, included})
        combinedEnvVars = [...repoDataToProcess.env];
      } else if (repoDataToProcess.env && typeof repoDataToProcess.env === 'object') { // From getRepository API (object of {key: {value, status}})
         combinedEnvVars = Object.entries(repoDataToProcess.env).map(([k, details]) => ({
          key: k, 
          value: details.value || '', 
          status: details.status || 'Optional', 
          included: details.status === 'Mandatory' ? true : (details.value ? true : false),
          source: 'gpt' // Mark source as GPT/backend suggestion
        }));
      }

      // 2. Process Dockerfile ENV vars (repoDataToProcess.dockerfile_env_vars)
      if (repoDataToProcess.dockerfile_env_vars && Array.isArray(repoDataToProcess.dockerfile_env_vars)) {
        const dockerfileEnvs = repoDataToProcess.dockerfile_env_vars.map(dfEnv => ({
          key: dfEnv.key,
          value: dfEnv.value || '',
          status: 'From Dockerfile', // Indicate source
          included: true, // Default to included for Dockerfile ENV vars
          source: 'dockerfile'
        }));

        // Merge: Add Dockerfile ENVs, prioritizing them if keys conflict, or simply appending.
        // For now, let's create a map of existing keys for quick lookup and update, then add new ones.
        const existingEnvMap = new Map(combinedEnvVars.map(env => [env.key, env]));
        dockerfileEnvs.forEach(dfEnv => {
          if (existingEnvMap.has(dfEnv.key)) {
            // If key exists, and source is different (e.g. GPT suggested something, Dockerfile has a default)
            // We can decide a rule: for now, let's assume Dockerfile default is strong, but let user override.
            // Let's update the value if it was from GPT and now Dockerfile provides one.
            // Or, simply let it be, user can manage. For this iteration, we just ensure it appears.
            // To avoid duplicates but show dockerfile version, remove old one if key matches.
            // This is a simple strategy: if Dockerfile has an ENV, it will be listed. If GPT also had it, it might be listed twice or overwritten.
            // A better merge would be to update existing entry's value/status if key matches and source is 'dockerfile'.
            // Current approach: remove existing from combinedEnvVars if key matches to avoid visual duplicate with different status/source.
            combinedEnvVars = combinedEnvVars.filter(env => env.key !== dfEnv.key);
            combinedEnvVars.push(dfEnv); // Add the Dockerfile version
          } else {
            combinedEnvVars.push(dfEnv); // Add new ENV from Dockerfile
          }
        });
      }
      setEnvVars(combinedEnvVars);

      // Fetch Dockerfile content if not passed in state and repo has dockerfile
      // (initialState might not include large content like dockerfile_content to keep URL short)
      if (repoDataToProcess.has_dockerfile && !repoDataToProcess.dockerfile_content) {
        getDockerfileContent(decodedRepoNameFromProps)
          .then(content => setDockerfileContent(content))
          .catch(err => console.error("Failed to fetch dockerfile content on deploy page:", err));
      } else if (repoDataToProcess.dockerfile_content) {
        setDockerfileContent(repoDataToProcess.dockerfile_content);
      }
    };

    if (initialStateParam) {
      try {
        const parsedState = JSON.parse(decodeURIComponent(initialStateParam));
        console.log("Received initialState for deployment:", parsedState);
        processRepoData(parsedState, 'initialStateParam');
        setLoading(false);
      } catch (err) {
        console.error("Error parsing initialState for deployment:", err);
        setError('Failed to load initial deployment configuration from state.');
        setLoading(false);
      }
    } else if (decodedRepoNameFromProps) {
      // Fallback to fetching if no initialState (e.g. navigating directly to deploy an existing repo)
      setLoading(true);
      setError(null);
      getRepository(decodedRepoNameFromProps)
        .then(repoData => {
          if (repoData) {
            processRepoData(repoData, 'API_fetch');
            // If also has_dockerfile, fetch its content separately if not included in repoData
            if (repoData.has_dockerfile) {
              return getDockerfileContent(decodedRepoNameFromProps);
            }
          }
          return null; // Or Promise.resolve(null) if getDockerfileContent not called
        })
        .then(dockerfile => {
          if (dockerfile) setDockerfileContent(dockerfile);
        })
        .catch(err => {
          console.error("Error fetching deployment data:", err);
          setError(err.response?.data?.detail || err.message || 'Failed to load repository deployment data.');
        })
        .finally(() => setLoading(false));
    } else {
      setError('Repository name not provided for deployment.');
      setLoading(false);
    }
  }, [repoName]); // Rely on repoName from props to re-trigger if necessary

  // Handlers for Container Arguments
  const handleContainerArgChange = (index, field, value) => {
    setContainerArgs(prev => prev.map((arg, i) => i === index ? { ...arg, [field]: value } : arg));
  };
  const handleAddContainerArg = () => {
    if (newContainerArgKey.trim()) {
      setContainerArgs(prev => [...prev, { key: newContainerArgKey.trim(), value: newContainerArgValue.trim() }]);
      setNewContainerArgKey('');
      setNewContainerArgValue('');
    }
  };
  const handleRemoveContainerArg = (index) => {
    setContainerArgs(prev => prev.filter((_, i) => i !== index));
  };

  const handleCheckDedicatedPort = async () => {
    const hostPort = parseInt(dedicatedHostPort, 10);
    if (isNaN(hostPort)) {
        setDedicatedPortCheckError('Please enter a valid number for the host port.');
        setDedicatedPortCheckResult(null);
        return;
    }

    setCheckingPort(hostPort);
    setDedicatedPortCheckResult(null);
    setDedicatedPortCheckError(null);
    setGenericPortCheckResult(null); // Clear other results
    setGenericPortCheckError(null);

    try {
        const result = await checkPortAvailability(hostPort);
        setDedicatedPortCheckResult(result);
    } catch (err) {
        console.error("Dedicated port check failed:", err);
        setDedicatedPortCheckError(err.response?.data?.detail || err.message || `Failed to check port ${hostPort}.`);
    } finally {
        setCheckingPort(null);
    }
  };

  const handleCheckPort = async (argIndex) => {
    const hostPort = parseInt(containerArgs[argIndex].value, 10);
    if (isNaN(hostPort)) {
        setGenericPortCheckError('Please enter a valid number for the port.');
        setGenericPortCheckResult(null);
        return;
    }

    setCheckingPort(hostPort);
    setGenericPortCheckResult(null);
    setGenericPortCheckError(null);
    setDedicatedPortCheckResult(null); // Clear other results
    setDedicatedPortCheckError(null);

    try {
        const result = await checkPortAvailability(hostPort);
        setGenericPortCheckResult(result);
    } catch (err) {
        console.error("Port check failed:", err);
        setGenericPortCheckError(err.response?.data?.detail || err.message || `Failed to check port ${hostPort}.`);
    } finally {
        setCheckingPort(null);
    }
  };

  // Handlers for Environment Variables
  const handleEnvVarChange = (index, field, value) => {
    setEnvVars(prev => prev.map((ev, i) => i === index ? { ...ev, [field]: value } : ev));
  };
  const handleAddEnvVar = () => {
    if (newEnvVarKey.trim()) {
      setEnvVars(prev => [...prev, { key: newEnvVarKey.trim(), value: newEnvVarValue.trim(), status: 'Optional', included: false}]); // New optional vars are not included by default
      setNewEnvVarKey('');
      setNewEnvVarValue('');
    }
  };
  const handleRemoveEnvVar = (index) => {
    setEnvVars(prev => prev.filter((_, i) => i !== index));
  };

  const handleDeploy = async () => {
    setDeploying(true);
    setDeployError(null);
    setDeploySuccess(null);
    setDeploymentLogs(''); // Clear previous logs
    setCurrentStage(DEPLOYMENT_STAGES.INIT);
    setStageDetails({
      [DEPLOYMENT_STAGES.INIT]: { status: 'pending', message: 'Preparing deployment...' }
    });

    const decodedRepoName = decodeURIComponent(repoName);

    // Validate port if dedicatedHostPort is set
    if (dedicatedHostPort) {
        const portNum = parseInt(dedicatedHostPort, 10);
        if (isNaN(portNum) || portNum <= 0 || portNum > 65535) {
            setDeployError("Invalid host port number. Must be between 1 and 65535.");
            setDeploying(false);
            return;
        }
        try {
            setCurrentStage(DEPLOYMENT_STAGES.VERIFYING_HEALTH);
            const portStatus = await checkPortAvailability(portNum);
            if (portStatus.status !== 'available') {
                setDeployError(portStatus.message || `Host port ${portNum} is not available.`);
                setDeploying(false);
                return;
            }
            setStageDetails(prev => ({
                ...prev,
                [DEPLOYMENT_STAGES.VERIFYING_HEALTH]: { status: 'success', message: `Host port ${portNum} is available.` }
            }));
        } catch (err) {
            setDeployError(`Error checking port ${portNum}: ${err.message || 'Unknown error'}`);
            setDeploying(false);
            return;
        }
    }

    const effectiveContainerArgs = {};
    containerArgs.forEach(arg => {
      if (arg.key) effectiveContainerArgs[arg.key] = arg.value;
    });

    // Add dedicated port mapping to containerArgs if set, ensuring it overrides others for mcpContainerPort
    if (dedicatedHostPort) {
      effectiveContainerArgs["-p"] = `${dedicatedHostPort}:${mcpContainerPort}/tcp`;
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.VERIFYING_HEALTH]: { status: 'success', message: `Mapping host port ${dedicatedHostPort} to container port ${mcpContainerPort}.` }
      }));
    }

    const effectiveEnvVars = {};
    envVars.filter(env => env.included && env.key).forEach(env => {
      effectiveEnvVars[env.key] = { value: env.value, status: env.status };
    });

    const deployPayload = {
      image_name: imageName,
      container_args: effectiveContainerArgs,
      env_vars: effectiveEnvVars,
      attempt_local_build: attemptLocalBuild,
      attempt_push_to_registry: attemptPushToRegistry,
      use_docker_compose: useCompose,
      // command and args for inside the container (from repo data, if applicable for single container)
      container_command: useCompose ? null : repository.command, 
      container_command_args: useCompose ? null : repository.args 
    };

    try {
      setCurrentStage(DEPLOYMENT_STAGES.INIT);
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.INIT]: { status: 'pending', message: 'Preparing repository entry...' }
      }));
      setDeploymentLogs(prevLogs => prevLogs + `\n[${new Date().toISOString()}] [${DEPLOYMENT_STAGES.INIT}] PREPARING: Ensuring repository entry exists...`);

      // Construct payload for saving/updating the repository core details
      const coreRepoData = {
        name: repository.name || decodedRepoName,
        repo_url: repository.repo_url,
        description: repository.description || "Deployed from Toolbox",
        command: repository.command, // Keep command/args as fetched
        args: repository.args,
        env: Object.fromEntries(envVars.filter(e => e.included && e.key).map(e => [e.key, { value: e.value || '', status: e.status || 'Optional' }])),
        has_dockerfile: repository.has_dockerfile || false,
        has_docker_compose: repository.has_docker_compose || false,
        deploy_as_container: true, // This is a container deployment
        is_external_config: false, // Not an external config at this stage
        docker_image_name_suggestion: imageName,
        exposed_port_suggestion: mcpContainerPort,
        container_args_template: repository.container_args_template || {},
        container_args_user: effectiveContainerArgs,
        deployment_status: 'pending_deployment', // Initial status before deploy call
        read_transport_sse_timeout_seconds: repository.read_transport_sse_timeout_seconds || 300,
        // Make sure all fields expected by RepositoryCreate Pydantic model are present with defaults if necessary
        transport: repository.transport || (useCompose ? 'compose_managed' : 'docker_managed'), // Example, adjust as per model
        url: repository.url || 'pending_deployment',
        headers: repository.headers || '{}',
      };
      
      await addOrUpdateRepository(coreRepoData.name, coreRepoData);
      setDeploymentLogs(prevLogs => prevLogs + `\n[${new Date().toISOString()}] [${DEPLOYMENT_STAGES.INIT}] PREPARED: Repository entry for ${coreRepoData.name} ensured.`);
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.INIT]: { status: 'pending', message: 'Starting deployment process...' }
      }));
      setDeploymentLogs(prevLogs => prevLogs + `\n[${new Date().toISOString()}] [${DEPLOYMENT_STAGES.INIT}] ${DEPLOYMENT_STAGES.INIT.toUpperCase()}: Starting deployment process...`);
      
      const deployResult = await deployContainer(decodedRepoName, deployPayload);
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.INIT]: { status: 'success', message: 'Deployment initiated.' }
      }));
      setDeploymentLogs(prevLogs => prevLogs + `\n[${new Date().toISOString()}] [${DEPLOYMENT_STAGES.INIT}] ${DEPLOYMENT_STAGES.INIT.toUpperCase()}: Deployment initiated. Response: ${JSON.stringify(deployResult, null, 2)}`);
      
      // deployResult for single container is { message, container_id }
      // deployResult for compose is { message, project_name, services }
      const deployedContainerIdOrProjectName = useCompose ? deployResult.project_name : deployResult.container_id;

      // If deployment is successful, proceed to finalize and save to DB
      setCurrentStage(DEPLOYMENT_STAGES.DEPLOYED);
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.DEPLOYED]: { status: 'pending', message: 'Finalizing and saving repository...' }
      }));
      setDeploymentLogs(prevLogs => prevLogs + `\n[${new Date().toISOString()}] [${DEPLOYMENT_STAGES.DEPLOYED}] ${DEPLOYMENT_STAGES.DEPLOYED.toUpperCase()}: Finalizing and saving repository...`);
      
      const mcpPath = "/mcp"; // Default, make configurable if needed

      const finalizePayload = {
        original_repo_name: repository.name || decodedRepoName,
        original_repo_url: repository.repo_url,
        description: repository.description,
        deployed_image_name: useCompose ? "N/A (compose)" : imageName, // Or derive from compose services if possible
        deployed_container_id_or_project_name: deployedContainerIdOrProjectName,
        host_port: dedicatedHostPort ? parseInt(dedicatedHostPort, 10) : null,
        mcp_container_port: mcpContainerPort, 
        mcp_path: mcpPath, 
        final_env_vars: Object.fromEntries(envVars.filter(e => e.included && e.key).map(e => [e.key, e.value || ""]) ),
        deployment_type: useCompose ? "compose" : "dockerfile", // Could be more granular
        command_suggestion: repository.command, // from original repo data
        args_suggestion: repository.args, // from original repo data
        has_dockerfile: repository.has_dockerfile,
        has_docker_compose: repository.has_docker_compose,
        dockerfile_content: repository.has_dockerfile ? dockerfileContent : null // Pass content if available
      };

      const savedRepository = await finalizeDeployment(finalizePayload);
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.DEPLOYED]: { status: 'success', message: 'Repository saved: ' + JSON.stringify(savedRepository, null, 2) }
      }));
      setDeploymentLogs(prevLogs => prevLogs + `\n[${new Date().toISOString()}] [${DEPLOYMENT_STAGES.DEPLOYED}] ${DEPLOYMENT_STAGES.DEPLOYED.toUpperCase()}: Repository saved: ${JSON.stringify(savedRepository, null, 2)}`);
      setDeploySuccess(true);
      setDeploymentLogs(prevLogs => prevLogs + `\n[SUCCESS] ${DEPLOYMENT_STAGES.DEPLOYED.toUpperCase()}: Successfully deployed and saved! Redirecting...`);
      
      setTimeout(() => {
        window.location.href = '/repositories';
      }, 2000);

    } catch (err) {
      console.error("Deployment process failed:", err);
      const errorDetail = err.detail || err.message || JSON.stringify(err);
      setStageDetails(prev => ({
        ...prev,
        [DEPLOYMENT_STAGES.FAILED]: { status: 'error', message: 'Deployment failed: ' + errorDetail }
      }));
      setDeployError(errorDetail);
      setDeploymentLogs(prevLogs => prevLogs + `\n[ERROR] ${DEPLOYMENT_STAGES.FAILED.toUpperCase()}: Deployment failed: ${errorDetail}`);
    } finally {
      setDeploying(false);
    }
  };
  
  // Helper to update the placeholder for the host port input
  const hostPortPlaceholder = `e.g., ${mcpContainerPort + 1}`;
  
  if (loading) return <div class="p-4">Loading deployment configuration...</div>;
  if (error) return <div class="p-4 text-red-600">Error: {error}</div>;
  if (!repository) return <div class="p-4">Repository data not found.</div>;

  return (
    <div className="bg-background-darker-wash text-text-primary min-h-screen p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-text-emphasis">Deploy Container: {repository?.name || decodeURIComponent(repoName)}</h1>
          <button 
            onClick={() => window.history.back()} 
            className="px-4 py-2 bg-background-light hover:bg-background-primary text-text-secondary rounded-md transition-colors duration-150 ease-in-out shadow"
          >
            Back
          </button>
      </div>

        {/* Loading and Error States */}
        {loading && <div className="text-center py-8"><div className="loader-lg"></div><p className="mt-2">Loading deployment configuration...</p></div>}
        {error && <div className="bg-red-800 border border-red-600 text-red-100 px-4 py-3 rounded relative mb-6" role="alert"><strong className="font-bold">Error:</strong><span className="block sm:inline"> {error}</span></div>}
        {deployError && <div className="bg-red-800 border border-red-600 text-red-100 px-4 py-3 rounded relative mb-6" role="alert"><strong className="font-bold">Deployment Error:</strong><span className="block sm:inline"> {deployError}</span><div className="mt-2 text-sm text-red-200 whitespace-pre-wrap">{deploymentLogs}</div></div>}
        {deploySuccess && <div className="bg-green-800 border border-green-600 text-green-100 px-4 py-3 rounded relative mb-6" role="alert"><strong className="font-bold">Success!</strong><span className="block sm:inline"> {deploySuccess}</span><div className="mt-2 text-sm text-green-200 whitespace-pre-wrap">{deploymentLogs}</div></div>}

        {repository && !loading && (
          <div className="space-y-8">
            {/* Dockerfile Content (if available and not using compose) */}
            {dockerfileContent && !useCompose && (
              <div className="bg-background-primary shadow-lg rounded-lg p-6">
                <h2 className="text-xl font-semibold mb-3 text-text-emphasis">Dockerfile Content</h2>
                <pre className="bg-background-darker-wash p-4 rounded-md overflow-x-auto max-h-96 text-sm text-text-secondary font-mono">{dockerfileContent}</pre>
              </div>
            )}

            {/* Docker Compose Mode Info (if applicable) */}
            {useCompose && (
                <div className="bg-indigo-800 border border-indigo-600 text-indigo-100 px-4 py-3 rounded relative mb-6" role="alert">
                    <strong className="font-bold">Docker Compose Mode:</strong>
                    <span className="block sm:inline"> This repository will be deployed using its <code>docker-compose.yml</code>. Port mappings and other settings are typically managed within the compose file itself. The options below might have limited effect.</span>
                </div>
            )}

            {/* Deployment Settings Form */}
            <form onSubmit={handleDeploy} className="bg-background-primary shadow-lg rounded-lg p-6 space-y-6">
              <h2 className="text-xl font-semibold mb-4 text-text-emphasis">Deployment Settings</h2>

              {/* Image Name */}
                <div>
                <label htmlFor="imageName" className="block text-sm font-medium text-text-secondary">Image Name</label>
                <input 
                  id="imageName" 
                  type="text" 
                  value={imageName} 
                  onChange={(e) => setImageName(e.target.value)} 
                  className="mt-1 block w-full px-3 py-2 bg-background-light border border-background-primary rounded-md shadow-sm focus:outline-none focus:ring-accent-primary focus:border-accent-primary sm:text-sm text-text-primary"
                  placeholder="e.g., myuser/myimage:latest"
                  required
                  disabled={useCompose} // Disable if using compose
                />
                <p className="mt-1 text-xs text-text-muted">The Docker image name and tag (e.g., yourusername/imagename:latest).</p>
                </div>

              {/* Exposed Host Port (conditionally rendered if not using compose) */}
              {!useCompose && (
                <div>
                  <label htmlFor="dedicatedHostPort" className="block text-sm font-medium text-text-secondary">
                    Exposed Host Port (maps to container port {mcpContainerPort})
                    </label>
                  <div className="mt-1 flex rounded-md shadow-sm">
                        <input 
                      id="dedicatedHostPort" 
                            type="text" 
                            value={dedicatedHostPort}
                      onChange={(e) => {
                        setDedicatedHostPort(e.target.value);
                        setDedicatedPortCheckResult(null); // Reset check result on change
                        setDedicatedPortCheckError(null);
                      }}
                      className="flex-1 block w-full min-w-0 px-3 py-2 bg-background-light border border-background-primary rounded-none rounded-l-md focus:ring-accent-primary focus:border-accent-primary sm:text-sm text-text-primary"
                      placeholder={hostPortPlaceholder}
                        />
                        <button 
                            type="button"
                            onClick={handleCheckDedicatedPort}
                      disabled={!dedicatedHostPort || checkingPort === parseInt(dedicatedHostPort, 10)}
                      className="inline-flex items-center px-3 py-2 border border-l-0 border-background-primary bg-background-light hover:bg-background-darker-wash text-text-secondary rounded-r-md text-sm font-medium disabled:opacity-50"
                        >
                      {checkingPort === parseInt(dedicatedHostPort, 10) ? 'Checking...' : 'Check Port'}
                        </button>
                    </div>
                  {dedicatedPortCheckResult && <p className={`mt-1 text-xs ${dedicatedPortCheckResult === 'available' ? 'text-green-400' : 'text-red-400'}`}>{dedicatedPortCheckResult === 'available' ? `Port ${dedicatedHostPort} is available.` : `Port ${dedicatedHostPort} is unavailable.`}</p>}
                  {dedicatedPortCheckError && <p className="mt-1 text-xs text-red-400">{dedicatedPortCheckError}</p>}
                  <p className="mt-1 text-xs text-text-muted">Enter the host port to map to container port {mcpContainerPort}. This will add/update the <code>-p {dedicatedHostPort}:{mcpContainerPort}</code> argument.</p>
                </div>
              )}

              {/* Build and Push Options (conditionally rendered if not using compose) */}
              {!useCompose && (
                <>
                  <div className="relative flex items-start">
                    <div className="flex items-center h-5">
                                <input
                                    id="attemptLocalBuild"
                                    name="attemptLocalBuild"
                                    type="checkbox"
                                    checked={attemptLocalBuild}
                                    onChange={(e) => setAttemptLocalBuild(e.target.checked)}
                        disabled={!repository?.has_dockerfile} // Disable if no Dockerfile
                        className="focus:ring-accent-primary h-4 w-4 text-accent-primary border-gray-600 rounded bg-background-light disabled:opacity-50"
                                />
                            </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor="attemptLocalBuild" className={`font-medium ${repository?.has_dockerfile ? 'text-text-secondary' : 'text-gray-500'}`}>
                                    Attempt to build image from local Dockerfile
                                </label>
                      <p className={`text-xs ${repository?.has_dockerfile ? 'text-text-muted' : 'text-gray-600'}`}>If unchecked (and Dockerfile exists), will try to pull the image name above directly.</p>
                      {!repository?.has_dockerfile && <p className="text-xs text-yellow-400">No Dockerfile detected in repository.</p>}
                    </div>
                  </div>

                  <div className="relative flex items-start">
                    <div className="flex items-center h-5">
                                <input
                                    id="attemptPushToRegistry"
                                    name="attemptPushToRegistry"
                                    type="checkbox"
                                    checked={attemptPushToRegistry}
                                    onChange={(e) => setAttemptPushToRegistry(e.target.checked)}
                        className="focus:ring-accent-primary h-4 w-4 text-accent-primary border-gray-600 rounded bg-background-light"
                                />
                            </div>
                    <div className="ml-3 text-sm">
                      <label htmlFor="attemptPushToRegistry" className="font-medium text-text-secondary">
                                    Push image to registry after successful build
                                </label>
                      <p className="text-xs text-text-muted">Requires Docker to be logged into the target registry for the image name above.</p>
                    </div>
                  </div>
                </>
                )}

                {/* Editable Container Arguments */}
              <div className="space-y-3">
                <h4 className="text-md font-medium text-text-secondary">Container Arguments</h4>
                <ul className="space-y-2">
                        {containerArgs.map((arg, index) => {
                            const isPortArg = arg.key === '-p' || arg.key === '--publish';
                            return (
                      <li key={`ca-${index}`} className="flex items-center space-x-2">
                        <input type="text" placeholder="Key (e.g., -p)" value={arg.key} onChange={(e) => handleContainerArgChange(index, 'key', e.target.value)} className="block w-1/3 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm" />
                        <input type="text" placeholder="Value (e.g., 8080:80)" value={arg.value} onChange={(e) => handleContainerArgChange(index, 'value', e.target.value)} className="block flex-1 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm" />
                                    
                                    {isPortArg && (
                                        <button 
                                            type="button" 
                                            onClick={() => handleCheckPort(index)}
                                            disabled={checkingPort !== null} // Disable if any port check is in progress
                            className="px-3 py-1.5 border border-blue-500 text-blue-500 text-xs font-medium rounded-md hover:bg-blue-50 disabled:opacity-50"
                                        >
                                            {checkingPort && arg.value.includes(String(checkingPort)) ? 'Checking...' : 'Check Port'}
                                        </button>
                                    )}
                        <button type="button" onClick={() => handleRemoveContainerArg(index)} className="text-red-500 hover:text-red-700 p-1.5 rounded-md hover:bg-red-50"><svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 10a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clipRule="evenodd" /></svg></button>
                                </li>
                            );
                        })}
                    </ul>
                     {/* Display Port Check Result/Error for generic args*/}
                     {(genericPortCheckResult || genericPortCheckError) && (
                  <div className={`mt-2 text-xs p-2 rounded-md ${genericPortCheckResult?.status === 'available' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                            {genericPortCheckError ? genericPortCheckError :
                             genericPortCheckResult ? genericPortCheckResult.message : ''}
                        </div>
                    )}
                <div className="flex items-center space-x-2 pt-2 border-t">
                  <input type="text" placeholder="New Argument Key" value={newContainerArgKey} onChange={(e) => setNewContainerArgKey(e.target.value)} className="block w-1/3 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm" />
                  <input type="text" placeholder="New Argument Value" value={newContainerArgValue} onChange={(e) => setNewContainerArgValue(e.target.value)} className="block flex-1 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm" />
                  <button type="button" onClick={handleAddContainerArg} disabled={!newContainerArgKey.trim()} className="inline-flex items-center justify-center p-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"><svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg></button>
                    </div>
                </div>

                {/* Editable Environment Variables */}
              <div className="space-y-3">
                <h4 className="text-md font-medium text-text-secondary">Environment Variables (for inside the container)</h4>
                 <div className="flex items-center space-x-2 mb-1 px-1 text-xs font-medium text-text-muted">
                    <div className="w-24 shrink-0">Status</div>
                    <div className="w-40 shrink-0">Included?</div> {/* Increased width for header */}
                    <div className="min-w-0 flex-1">Key</div>
                    <div className="min-w-0 flex-1">Value</div>
                    <div className="w-10 shrink-0"></div>
                    </div>
                  <ul className="space-y-2">
                        {envVars.map((ev, index) => (
                      <li key={`env-${index}`} className="flex items-center space-x-2">
                        <div className="w-24 shrink-0">
                          <span className={`px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${ev.status === 'Mandatory' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{ev.status}</span>
                                </div>
                        <div className="w-40 shrink-0 flex items-center"> {/* Ensure checkbox is vertically centered if needed */}
                                    <input 
                                        type="checkbox" 
                                        checked={ev.included} 
                                        disabled={ev.status === 'Mandatory'}
                                        onChange={(e) => handleEnvVarChange(index, 'included', e.target.checked)}
                            className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-50 disabled:bg-gray-200"
                                    />
                                </div>
                        <input type="text" placeholder="Key" value={ev.key} readOnly={ev.status === 'Mandatory' || (ev.status === 'Optional' && !ev.included)} onChange={(e) => handleEnvVarChange(index, 'key', e.target.value)} className={`block min-w-0 flex-1 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm ${(ev.status === 'Mandatory' || (ev.status === 'Optional' && !ev.included)) ? 'bg-gray-50 text-gray-500' : ''}`} />
                        <input type="text" placeholder="Value" value={ev.value} readOnly={ev.status === 'Optional' && !ev.included} onChange={(e) => handleEnvVarChange(index, 'value', e.target.value)} className={`block min-w-0 flex-1 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm ${(ev.status === 'Optional' && !ev.included) ? 'bg-gray-50 text-gray-500' : ''}`} />
                        <button type="button" onClick={() => handleRemoveEnvVar(index)} className="text-red-500 hover:text-red-700 p-1.5 rounded-md hover:bg-red-50"><svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M6 10a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1z" clipRule="evenodd" /></svg></button>
                            </li>
                        ))}
                    </ul>
                  <div className="flex items-center space-x-2 pt-2 border-t">
                    <div className="w-24 shrink-0"></div> {/* Spacer for status */}
                    <div className="w-40 shrink-0"></div> {/* Spacer for included checkbox */}
                    <input type="text" placeholder="New Variable Key" value={newEnvVarKey} onChange={(e) => setNewEnvVarKey(e.target.value)} className="block min-w-0 flex-1 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm" />
                    <input type="text" placeholder="New Variable Value" value={newEnvVarValue} onChange={(e) => setNewEnvVarValue(e.target.value)} className="block min-w-0 flex-1 px-3 py-1.5 border border-gray-300 rounded-md shadow-sm text-sm" />
                    <button type="button" onClick={handleAddEnvVar} disabled={!newEnvVarKey.trim()} className="inline-flex items-center justify-center p-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"><svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" /></svg></button>
                    </div>
                </div>
            </form>

            <div className="flex justify-end pt-5">
              <button type="button" onClick={() => window.history.back()} className="bg-background-light py-2 px-4 border border-gray-300 rounded-md shadow-sm text-text-secondary hover:bg-background-primary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-primary disabled:opacity-50" disabled={deploying}>Cancel</button>
              <button type="button" onClick={handleDeploy} className="ml-3 inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-accent-primary hover:bg-accent-secondary focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-primary disabled:opacity-50" disabled={deploying}>
          {deploying ? 'Deploying...' : 'Deploy Container'}
        </button>
      </div>

      {/* Deployment Status & Logs Section */}
      {(deploying || deployError || deploySuccess || Object.keys(stageDetails).length > 0) && (
              <div className="mt-6 bg-background-primary shadow sm:rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <h3 className="text-lg leading-6 font-medium text-text-emphasis">Deployment Progress</h3>
                  <div className="mt-4 space-y-3">
              {Object.entries(DEPLOYMENT_STAGES).map(([key, stageName]) => {
                      if (stageName === DEPLOYMENT_STAGES.FAILED && (!deployError && !Object.values(stageDetails).some(s => s.status === 'error'))) return null;
                      if (stageName === DEPLOYMENT_STAGES.DEPLOYED && !deploySuccess) return null;
                
                const stageInfo = stageDetails[stageName];
                      let bgColor = 'bg-background-light';
                      let textColor = 'text-text-secondary';
                      let statusIcon = <span className="h-2 w-2 bg-gray-400 rounded-full"></span>;

                if (stageInfo?.status === 'success') {
                  bgColor = 'bg-green-50';
                  textColor = 'text-green-700';
                        statusIcon = <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" /></svg>;
                } else if (stageInfo?.status === 'error') {
                  bgColor = 'bg-red-50';
                  textColor = 'text-red-700';
                        statusIcon = <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" /></svg>;
                } else if (stageInfo?.status === 'pending' || (deploying && currentStage === stageName)){
                   bgColor = 'bg-blue-50';
                   textColor = 'text-blue-700';
                   statusIcon = (
                          <svg className="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                   );
                }

                return (
                        <div key={stageName} className={`p-3 rounded-md shadow-sm ${bgColor}`}>
                          <div className="flex items-center space-x-3">
                            <div className="flex-shrink-0">
                        {statusIcon}
                      </div>
                            <div className={`flex-1 min-w-0 ${textColor}`}>
                              <p className="text-sm font-medium">{stageName}</p>
                              {stageInfo?.message && <p className="text-xs truncate">{stageInfo.message}</p>}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Original verbose log display */}
            {deploymentLogs && (
                    <div className="mt-4">
                        <h4 className="text-md font-medium text-text-secondary mb-1">Verbose Deployment Logs:</h4>
                        <pre className="p-3 bg-background-darker-wash text-text-secondary text-xs rounded-md overflow-x-auto max-h-96">
                      <code>{deploymentLogs}</code>
                  </pre>
              </div>
            )}
          </div>
        </div>
      )}
          </div>
        )}
      </div>
    </div>
  );
} 