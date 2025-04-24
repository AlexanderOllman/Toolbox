import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Typography, 
  TextField, 
  Button, 
  Box, 
  Paper, 
  Alert, 
  CircularProgress, 
  Divider, 
  Grid, 
  Chip,
  Tooltip,
  IconButton
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import { getSettings, updateSettings, testQdrantConnection } from '../services/api';

const VectorSettings = () => {
  const [settings, setSettings] = useState({
    QDRANT_HOST: '',
    QDRANT_PORT: '',
    OPENAI_API_KEY: '',
    COLLECTION_NAME: '',
    QDRANT_STATUS: 'unknown',
    MCP_REPO_PATH: ''
  });
  const [loading, setLoading] = useState(true);
  const [testingConnection, setTestingConnection] = useState(false);
  const [refreshingStatus, setRefreshingStatus] = useState(false);
  const [saveStatus, setSaveStatus] = useState({ message: '', severity: 'info' });
  const [testStatus, setTestStatus] = useState({ message: '', severity: 'info' });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const data = await getSettings();
      setSettings(data);
    } catch (error) {
      setSaveStatus({
        message: `Error fetching settings: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const refreshConnectionStatus = async () => {
    try {
      setRefreshingStatus(true);
      const response = await testQdrantConnection();
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: response.status === 'success' ? 'connected' : 'disconnected'
      }));
    } catch (error) {
      console.error('Error refreshing connection status:', error);
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: 'disconnected'
      }));
    } finally {
      setRefreshingStatus(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setSettings(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      setLoading(true);
      setSaveStatus({ message: '', severity: 'info' });
      
      const configItems = Object.entries(settings)
        .filter(([key]) => key !== 'QDRANT_STATUS') // Exclude status field
        .map(([key, value]) => ({
          key,
          value
        }));
      
      // Log the items being sent
      console.log('Saving settings:', configItems);
      
      const response = await updateSettings(configItems);
      
      setSaveStatus({
        message: response.message || 'Settings saved successfully',
        severity: 'success'
      });

      // Explicitly verify that settings were saved by fetching them again
      const updatedSettings = await getSettings();
      console.log('Retrieved settings after save:', updatedSettings);
      setSettings(prevSettings => ({
        ...updatedSettings,
        QDRANT_STATUS: prevSettings.QDRANT_STATUS // Preserve connection status
      }));

      // After updating settings, refresh connection status
      await refreshConnectionStatus();
    } catch (error) {
      setSaveStatus({
        message: `Error saving settings: ${error.message}`,
        severity: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestQdrantConnection = async () => {
    try {
      setTestingConnection(true);
      setTestStatus({ message: '', severity: 'info' });
      
      // Save current values first to ensure we test against the values in the form
      const currentSettings = {
        QDRANT_HOST: settings.QDRANT_HOST,
        QDRANT_PORT: settings.QDRANT_PORT,
        COLLECTION_NAME: settings.COLLECTION_NAME
      };
      
      console.log('Testing connection with:', currentSettings);
      
      // Save current form values first so test uses these values
      const configItems = Object.entries(currentSettings).map(([key, value]) => ({
        key, value
      }));
      
      // Apply settings before testing
      await updateSettings(configItems);
      
      // Now test the connection
      const response = await testQdrantConnection();
      
      setTestStatus({
        message: response.message,
        severity: response.status === 'success' ? 'success' : 'error'
      });

      // Update connection status
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: response.status === 'success' ? 'connected' : 'disconnected'
      }));
    } catch (error) {
      setTestStatus({
        message: `Error testing connection: ${error.message}`,
        severity: 'error'
      });
      
      setSettings(prev => ({
        ...prev,
        QDRANT_STATUS: 'disconnected'
      }));
    } finally {
      setTestingConnection(false);
    }
  };

  const getConnectionStatusColor = () => {
    switch (settings.QDRANT_STATUS) {
      case 'connected':
        return 'success';
      case 'disconnected':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading && Object.values(settings).every(v => v === '' || v === 'unknown')) {
    return (
      <Container sx={{ mt: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h4" gutterBottom>
            Vector Database Settings
          </Typography>
          <Box display="flex" alignItems="center">
            <Typography variant="body2" color="text.secondary" mr={1}>
              Connection Status:
            </Typography>
            <Chip 
              label={settings.QDRANT_STATUS === 'connected' ? 'Connected' : 'Disconnected'} 
              color={getConnectionStatusColor()} 
              size="small" 
              sx={{ mr: 1 }}
            />
            <Tooltip title="Refresh connection status">
              <IconButton 
                size="small" 
                onClick={refreshConnectionStatus}
                disabled={refreshingStatus}
              >
                {refreshingStatus ? <CircularProgress size={18} /> : <RefreshIcon fontSize="small" />}
              </IconButton>
            </Tooltip>
          </Box>
        </Box>
        <Typography variant="body1" color="text.secondary" paragraph>
          Configure the connection to Qdrant vector database and OpenAI API for semantic search capabilities.
        </Typography>

        <Divider sx={{ my: 3 }} />

        <form onSubmit={handleSubmit}>
          <Typography variant="h6" gutterBottom>
            MCP Repository Settings
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="MCP Repository Path"
                name="MCP_REPO_PATH"
                value={settings.MCP_REPO_PATH || ''}
                onChange={handleInputChange}
                margin="normal"
                variant="outlined"
                placeholder="/Users/yourname/Documents/Toolbox"
                helperText="Directory where MCP repositories will be cloned (defaults to Toolbox directory)"
              />
            </Grid>
          </Grid>

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            Qdrant Settings
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={8}>
              <TextField
                fullWidth
                label="Qdrant Host"
                name="QDRANT_HOST"
                value={settings.QDRANT_HOST || ''}
                onChange={handleInputChange}
                margin="normal"
                variant="outlined"
                placeholder="localhost"
                helperText="Hostname or IP address of Qdrant server"
              />
            </Grid>
            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Qdrant Port"
                name="QDRANT_PORT"
                value={settings.QDRANT_PORT || ''}
                onChange={handleInputChange}
                margin="normal"
                variant="outlined"
                placeholder="6333"
                helperText="Port number"
              />
            </Grid>
          </Grid>

          <TextField
            fullWidth
            label="Collection Name"
            name="COLLECTION_NAME"
            value={settings.COLLECTION_NAME || ''}
            onChange={handleInputChange}
            margin="normal"
            variant="outlined"
            placeholder="mcp_servers"
            helperText="Name of the collection in Qdrant for storing repository embeddings"
          />

          <Box sx={{ display: 'flex', justifyContent: 'flex-start', mt: 1, mb: 3 }}>
            <Button 
              variant="outlined" 
              onClick={handleTestQdrantConnection}
              disabled={testingConnection || !settings.QDRANT_HOST}
              startIcon={testingConnection ? <CircularProgress size={20} /> : null}
            >
              {testingConnection ? 'Testing...' : 'Test Connection'}
            </Button>
          </Box>

          {testStatus.message && (
            <Alert severity={testStatus.severity} sx={{ mb: 3 }}>
              {testStatus.message}
            </Alert>
          )}

          <Divider sx={{ my: 3 }} />

          <Typography variant="h6" gutterBottom>
            OpenAI API Settings
          </Typography>
          <TextField
            fullWidth
            label="OpenAI API Key"
            name="OPENAI_API_KEY"
            value={settings.OPENAI_API_KEY || ''}
            onChange={handleInputChange}
            margin="normal"
            variant="outlined"
            type="password"
            helperText="Required for generating embeddings"
          />

          <Box sx={{ mt: 4, display: 'flex', justifyContent: 'space-between' }}>
            <Button 
              variant="outlined" 
              onClick={fetchSettings} 
              disabled={loading}
            >
              Reset
            </Button>
            <Button 
              type="submit" 
              variant="contained" 
              color="primary" 
              disabled={loading}
              startIcon={loading ? <CircularProgress size={20} /> : null}
            >
              Save Settings
            </Button>
          </Box>

          {saveStatus.message && (
            <Alert severity={saveStatus.severity} sx={{ mt: 3 }}>
              {saveStatus.message}
            </Alert>
          )}
        </form>
      </Paper>
    </Container>
  );
};

export default VectorSettings; 