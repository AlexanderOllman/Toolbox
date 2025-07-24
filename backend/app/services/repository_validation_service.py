import os
import logging
from typing import Optional, Dict, Any, List, Tuple
from app.services.config_service import get_mcp_repo_path
from app.services.database import get_repository

logger = logging.getLogger(__name__)

class RepositoryValidationService:
    """Service for validating repository existence, paths, and deployment readiness."""
    
    @staticmethod
    def find_repository_path(repo_name: str, repo_url: Optional[str] = None) -> Optional[str]:
        """
        Find the actual path where a repository is stored locally.
        
        Args:
            repo_name: The repository name
            repo_url: Optional repository URL to derive folder name
            
        Returns:
            The actual path if found, None otherwise
        """
        base_dir = get_mcp_repo_path()
        
        # Generate possible paths
        possible_paths = [repo_name]  # Direct name match
        
        if repo_url:
            # Derive folder name from URL
            cloned_repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
            if cloned_repo_name != repo_name:
                possible_paths.append(cloned_repo_name)
        
        # Check each possible path
        for path_candidate in possible_paths:
            full_path = os.path.join(base_dir, path_candidate)
            if os.path.isdir(full_path):
                logger.info(f"Found repository '{repo_name}' at {full_path}")
                return full_path
        
        logger.warning(f"Repository '{repo_name}' not found in any of: {[os.path.join(base_dir, p) for p in possible_paths]}")
        return None
    
    @staticmethod
    def validate_repository_for_deployment(repo_name: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate that a repository is ready for deployment or synchronization.
        If called for synchronization (repo not in DB), it will still analyze local files.
        
        Args:
            repo_name: The repository name
            
        Returns:
            Tuple of (is_valid_for_db_or_sync_analysis, error_message, repository_info)
        """
        repo = get_repository(repo_name)
        repo_info = {
            'in_database': repo is not None,
            'repo_data': repo,
            'local_path': None,
            'has_dockerfile': False,
            'has_docker_compose': False,
            'dockerfile_path': None,
            'compose_files': []
        }
        
        repo_url_for_path_finding = repo.get("repo_url") if repo else None
        local_path = RepositoryValidationService.find_repository_path(repo_name, repo_url_for_path_finding)

        if not local_path:
            if repo:
                return False, f"Repository '{repo_name}' found in database but not cloned locally. Please re-fetch repository details.", repo_info
            else:
                return False, f"Repository '{repo_name}' not found in database or local file system.", repo_info
        
        repo_info['local_path'] = local_path
        
        # Always analyze local files if path is found, regardless of DB status
        dockerfile_path_val = os.path.join(local_path, "Dockerfile")
        if os.path.isfile(dockerfile_path_val):
            repo_info['has_dockerfile'] = True
            repo_info['dockerfile_path'] = dockerfile_path_val
        
        compose_file_names = ['docker-compose.yml', 'docker-compose.yaml']
        found_compose_files_list = []
        for cf_name in compose_file_names:
            compose_path_val = os.path.join(local_path, cf_name)
            if os.path.isfile(compose_path_val):
                found_compose_files_list.append(compose_path_val)
        
        if found_compose_files_list:
            repo_info['has_docker_compose'] = True
            repo_info['compose_files'] = found_compose_files_list

        if repo is None:
            # If not in DB, but found and analyzed locally, it's valid for sync but might need DB setup for full deploy readiness.
            # The error message from sync_local_repository will guide the user if it already exists.
            # For the purpose of this validation function, if we found it locally and analyzed, return True.
            return True, f"Repository '{repo_name}' found locally and analyzed, but not yet in database.", repo_info
        
        # If in DB and path found & analyzed, it's valid.
        return True, "", repo_info
    
    @staticmethod
    def validate_deployment_requirements(repo_info: Dict[str, Any], deployment_config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate that deployment requirements are met.
        
        Args:
            repo_info: Repository information from validate_repository_for_deployment
            deployment_config: Deployment configuration (e.g., use_docker_compose, attempt_local_build)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not repo_info.get('in_database'):
            return False, "Repository must be saved to database before deployment"
        
        if not repo_info.get('local_path'):
            return False, "Repository must be cloned locally before deployment"
        
        # Check Docker Compose requirements
        if deployment_config.get('use_docker_compose', False):
            if not repo_info.get('has_docker_compose'):
                return False, "Docker Compose deployment requested but no docker-compose.yml file found"
        
        # Check local build requirements
        if deployment_config.get('attempt_local_build', False):
            if not repo_info.get('has_dockerfile'):
                return False, "Local build requested but no Dockerfile found"
        
        return True, ""
    
    @staticmethod
    def get_dockerfile_content(repo_name: str) -> Tuple[bool, str, Optional[str]]:
        """
        Get Dockerfile content for a repository.
        
        Args:
            repo_name: The repository name
            
        Returns:
            Tuple of (success, error_message, dockerfile_content)
        """
        is_valid, error_msg, repo_info = RepositoryValidationService.validate_repository_for_deployment(repo_name)
        
        if not is_valid:
            return False, error_msg, None
        
        if not repo_info.get('has_dockerfile'):
            return False, f"No Dockerfile found in repository '{repo_name}'", None
        
        dockerfile_path = repo_info.get('dockerfile_path')
        if not dockerfile_path:
            return False, f"Dockerfile path not determined for repository '{repo_name}'", None
        
        try:
            with open(dockerfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.info(f"Successfully read Dockerfile for {repo_name} from {dockerfile_path}")
            return True, "", content
        except Exception as e:
            logger.error(f"Error reading Dockerfile for {repo_name}: {e}")
            return False, f"Failed to read Dockerfile: {str(e)}", None 