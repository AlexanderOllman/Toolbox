import subprocess
import os
import sys
import venv

def setup_backend_venv(backend_path):
    venv_path = os.path.join(backend_path, "venv")
    python_exec = os.path.join(venv_path, "bin", "python3") if os.name != 'nt' else os.path.join(venv_path, "Scripts", "python.exe")
    pip_exec = os.path.join(venv_path, "bin", "pip") if os.name != 'nt' else os.path.join(venv_path, "Scripts", "pip.exe")

    if not os.path.isdir(venv_path):
        print("🔧 Creating virtual environment for backend...")
        venv.EnvBuilder(with_pip=True).create(venv_path)

    print("📦 Installing backend dependencies...")
    subprocess.run([pip_exec, "install", "-r", "requirements.txt"], cwd=backend_path, check=True)

    return python_exec

def run_services():
    backend_path = os.path.join(os.getcwd(), "backend")
    frontend_path = os.path.join(os.getcwd(), "frontend")

    if not os.path.isdir(backend_path):
        print("❌ Backend directory not found.")
        return
    if not os.path.isdir(frontend_path):
        print("❌ Frontend directory not found.")
        return

    # Setup and get the backend Python interpreter
    backend_python = setup_backend_venv(backend_path)

    print("🚀 Starting backend and frontend...")

    backend_proc = subprocess.Popen(
        [backend_python, "run.py"],
        cwd=backend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    try:
        while True:
            backend_line = backend_proc.stdout.readline()
            if backend_line:
                print(f"[Backend] {backend_line.strip()}")

            frontend_line = frontend_proc.stdout.readline()
            if frontend_line:
                print(f"[Frontend] {frontend_line.strip()}")
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("✅ Both services terminated.")

if __name__ == "__main__":
    run_services()
