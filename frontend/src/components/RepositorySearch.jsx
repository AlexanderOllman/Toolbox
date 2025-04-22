import React, { useState, useEffect } from 'react';
import { 
  Box, 
  TextField, 
  IconButton, 
  InputAdornment,
  Typography,
  Paper,
  List,
  ListItem,
  ListItemText,
  Divider,
  Chip,
  CircularProgress,
  Alert
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CodeIcon from '@mui/icons-material/Code';
import { Link } from 'react-router-dom';
import { searchRepositories, getQdrantStatus } from '../services/api';

const RepositorySearch = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [connectionStatus, setConnectionStatus] = useState('unknown');
  const [checkingStatus, setCheckingStatus] = useState(true);

  useEffect(() => {
    checkQdrantStatus();
  }, []);

  const checkQdrantStatus = async () => {
    try {
      setCheckingStatus(true);
      const status = await getQdrantStatus();
      setConnectionStatus(status.status);
    } catch (error) {
      console.error('Error checking Qdrant status:', error);
      setConnectionStatus('disconnected');
    } finally {
      setCheckingStatus(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) return;
    
    try {
      setLoading(true);
      setError('');
      
      // Check status before searching
      await checkQdrantStatus();
      
      if (connectionStatus !== 'connected') {
        setError('Vector search unavailable: Qdrant is not connected.');
        setResults([]);
        return;
      }
      
      const data = await searchRepositories(query, 5);
      setResults(data);
    } catch (error) {
      setError('Failed to search repositories. Please try again.');
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatScore = (score) => {
    return (score * 100).toFixed(1) + '%';
  };

  return (
    <Box sx={{ mb: 4 }}>
      {connectionStatus === 'disconnected' && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Vector search is currently unavailable because Qdrant is not connected.
          <Link to="/vector-settings" style={{ marginLeft: 8 }}>
            Check settings
          </Link>
        </Alert>
      )}
      
      <form onSubmit={handleSearch}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search repositories with natural language..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton 
                  color="primary" 
                  type="submit" 
                  disabled={loading || !query.trim() || checkingStatus || connectionStatus === 'disconnected'}
                >
                  {loading ? <CircularProgress size={24} /> : <SearchIcon />}
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </form>

      {error && (
        <Typography color="error" variant="body2" sx={{ mt: 1 }}>
          {error}
        </Typography>
      )}

      {results.length > 0 && (
        <Paper sx={{ mt: 2 }}>
          <List>
            {results.map((repo, index) => (
              <React.Fragment key={repo.name}>
                {index > 0 && <Divider />}
                <ListItem
                  component={Link}
                  to={`/repositories?name=${encodeURIComponent(repo.name)}`}
                  sx={{ 
                    textDecoration: 'none', 
                    color: 'inherit',
                    '&:hover': {
                      backgroundColor: 'rgba(0, 0, 0, 0.04)'
                    }
                  }}
                >
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <CodeIcon sx={{ mr: 1 }} color="primary" />
                          <Typography variant="subtitle1">{repo.name}</Typography>
                        </Box>
                        <Chip 
                          label={`Match: ${formatScore(repo.score)}`} 
                          size="small" 
                          color="primary" 
                          variant="outlined"
                        />
                      </Box>
                    }
                    secondary={repo.description}
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};

export default RepositorySearch; 