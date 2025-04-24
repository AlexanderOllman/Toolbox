import subprocess
import os

def run_services():
    backend_path = os.path.join(os.getcwd(), "backend")
    frontend_path = os.path.join(os.getcwd(), "frontend")

    # Ensure the paths exist
    if not os.path.isdir(backend_path):
        print("❌ Backend directory not found.")
        return
    if not os.path.isdir(frontend_path):
        print("❌ Frontend directory not found.")
        return

    print("🚀 Starting backend and frontend...")

    backend_proc = subprocess.Popen(
        ["python3", "run.py"],
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
