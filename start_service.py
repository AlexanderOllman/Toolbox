import subprocess
import os
import sys
import venv
import shutil # Added for shutil.which
import logging # Added for logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_backend_venv(backend_path):
    # Prioritize Docker check
    if os.environ.get('IN_DOCKER'):
        logger.info("📦 IN_DOCKER is true, skipping backend venv setup.")
        return 'python' # Use system python installed in Docker image

    # --- Code below only runs if NOT in Docker ---
    logger.info("🔧 Not in Docker, setting up backend venv...")
    venv_path = os.path.join(backend_path, "venv")
    python_exec = os.path.join(venv_path, "bin", "python3") if os.name != 'nt' else os.path.join(venv_path, "Scripts", "python.exe")
    pip_exec = os.path.join(venv_path, "bin", "pip") if os.name != 'nt' else os.path.join(venv_path, "Scripts", "pip.exe")

    if not os.path.isdir(venv_path):
        logger.info("🔧 Creating virtual environment for backend...")
        try:
            venv.EnvBuilder(with_pip=True).create(venv_path)
        except Exception as e:
            logger.error(f"❌ Error creating venv: {e}")
            sys.exit(1) # Exit if venv creation fails

    logger.info("📦 Installing backend dependencies using venv pip...")
    try:
        # Ensure pip_exec exists before running
        if not os.path.exists(pip_exec):
             logger.error(f"❌ Error: pip executable not found at {pip_exec}")
             sys.exit(1)
        
        subprocess.run([pip_exec, "install", "-r", "requirements.txt"], cwd=backend_path, check=True, capture_output=True, text=True)
        logger.info("✅ Backend dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error installing backend dependencies: {e}")
        logger.error(f"   Pip stdout: {e.stdout}")
        logger.error(f"   Pip stderr: {e.stderr}")
        sys.exit(1) # Exit if installation fails
    except FileNotFoundError as e:
        logger.error(f"❌ FileNotFoundError during pip install: {e}")
        logger.error(f"   Attempted to run: {pip_exec}")
        sys.exit(1)

    return python_exec

def setup_frontend(frontend_path):
    # Prioritize Docker check
    if os.environ.get('IN_DOCKER'):
        logger.info("📦 IN_DOCKER is true, skipping frontend setup.")
        return # Skip setup

    # --- Code below only runs if NOT in Docker ---
    logger.info("🔧 Not in Docker, setting up frontend...")
    node_modules_path = os.path.join(frontend_path, "node_modules")
    if not os.path.isdir(node_modules_path):
        logger.info("📦 Installing frontend dependencies with npm install...")
        try:
            # Check if npm exists
            npm_path = shutil.which("npm")
            if not npm_path:
                 logger.error("❌ Error: npm command not found.")
                 sys.exit(1)
            subprocess.run([npm_path, "install"], cwd=frontend_path, check=True, capture_output=True, text=True)
            logger.info("✅ Frontend dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Error installing frontend dependencies: {e}")
            logger.error(f"   Npm stdout: {e.stdout}")
            logger.error(f"   Npm stderr: {e.stderr}")
            sys.exit(1) # Exit if installation fails
        except FileNotFoundError as e:
             logger.error(f"❌ FileNotFoundError during npm install: {e}")
             sys.exit(1)

def run_services():
    backend_path = os.path.join(os.getcwd(), "backend")
    frontend_path = os.path.join(os.getcwd(), "frontend")

    if not os.path.isdir(backend_path):
        logger.error("❌ Backend directory not found.")
        return
    if not os.path.isdir(frontend_path):
        logger.error("❌ Frontend directory not found.")
        return

    backend_python = setup_backend_venv(backend_path)
    setup_frontend(frontend_path)

    logger.info("🚀 Starting backend and frontend...")

    # For Docker, bind to 0.0.0.0 instead of localhost to allow external access
    host_arg = "--host=0.0.0.0" if os.environ.get('IN_DOCKER') else ""
    
    backend_command = [backend_python, "run.py", host_arg] if host_arg else [backend_python, "run.py"]
    # Filter out empty strings from command list
    backend_command = [arg for arg in backend_command if arg]
    
    logger.info(f"Running backend command: {' '.join(backend_command)}")
    backend_proc = subprocess.Popen(
        backend_command,
        cwd=backend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # For Docker, configure Vite to listen on all interfaces
    dev_command = ["npm", "run", "dev", "--", "--host=0.0.0.0"] if os.environ.get('IN_DOCKER') else ["npm", "run", "dev"]
    
    logger.info(f"Running frontend command: {' '.join(dev_command)}")
    frontend_proc = subprocess.Popen(
        dev_command,
        cwd=frontend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        while True:
            backend_line = backend_proc.stdout.readline()
            if backend_line:
                logger.info(f"[Backend] {backend_line.strip()}")

            frontend_line = frontend_proc.stdout.readline()
            if frontend_line:
                logger.info(f"[Frontend] {frontend_line.strip()}")
            
            # Check if processes have exited
            if backend_proc.poll() is not None and frontend_proc.poll() is not None:
                logger.warning("Both processes seem to have exited.")
                break
            elif backend_proc.poll() is not None:
                logger.warning("Backend process seems to have exited.")
                # Optionally handle frontend process termination here
            elif frontend_proc.poll() is not None:
                 logger.warning("Frontend process seems to have exited.")
                 # Optionally handle backend process termination here

    except KeyboardInterrupt:
        logger.info("\n🛑 Stopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        logger.info("✅ Both services terminated.")
    except Exception as e:
        logger.error(f"🚨 An error occurred while monitoring services: {e}")
    finally:
        # Ensure processes are terminated if loop exits unexpectedly
        if backend_proc.poll() is None:
            backend_proc.terminate()
            backend_proc.wait()
        if frontend_proc.poll() is None:
            frontend_proc.terminate()
            frontend_proc.wait()

if __name__ == "__main__":
    run_services()
