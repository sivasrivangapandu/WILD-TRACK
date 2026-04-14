"""
Watchdog for WildTrackAI backend - monitors and auto-restarts if crashed.
Run this in a separate terminal: python backend_watchdog.py
"""

import os
import sys
import time
import subprocess
import requests
import signal
from pathlib import Path
from datetime import datetime

class BackendWatchdog:
    def __init__(self):
        self.backend_process = None
        self.running = True
        self.backend_dir = Path(__file__).parent / ".." / "backend"
        self.check_interval = 5  # Check every 5 seconds
        self.restart_count = 0
        self.max_restarts = 5
        self.restart_cooldown = 10
        self.last_restart = None
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def log(self, level, msg):
        """Log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level:8s}] {msg}")
    
    def handle_shutdown(self, signum, frame):
        """Handle graceful shutdown."""
        self.log("INFO", "Shutdown signal received")
        self.running = False
        if self.backend_process:
            self.log("INFO", "Terminating backend process...")
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
            except:
                self.backend_process.kill()
        sys.exit(0)
    
    def is_backend_healthy(self):
        """Check if backend is responding to health check."""
        try:
            response = requests.get("http://localhost:8000/health", timeout=3)
            return response.status_code in [200, 503]  # 503 means server is up but model loading
        except:
            return False
    
    def start_backend(self):
        """Start the backend process."""
        if self.last_restart and (time.time() - self.last_restart) < self.restart_cooldown:
            self.log("WARN", f"Restart cooldown active ({self.restart_cooldown}s)")
            return False
        
        if self.restart_count >= self.max_restarts:
            self.log("ERROR", f"Max restarts ({self.max_restarts}) reached. Giving up.")
            self.running = False
            return False
        
        self.log("INFO", "Starting backend process...")
        
        try:
            # Use .venv if it exists
            venv_path = self.backend_dir / ".venv" / "Scripts" / "python.exe"
            if not venv_path.exists():
                venv_path = self.backend_dir / "venv" / "Scripts" / "python.exe"
            if not venv_path.exists():
                venv_path = sys.executable  # Fallback to system Python
            
            self.backend_process = subprocess.Popen(
                [str(venv_path), "main.py"],
                cwd=str(self.backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1,
            )
            
            self.restart_count += 1
            self.last_restart = time.time()
            self.log("INFO", f"Backend process started (PID: {self.backend_process.pid})")
            return True
            
        except Exception as e:
            self.log("ERROR", f"Failed to start backend: {e}")
            return False
    
    def check_backend(self):
        """Check backend status and restart if needed."""
        if self.backend_process is None:
            return self.start_backend()
        
        # Check if process is still running
        if self.backend_process.poll() is not None:
            retcode = self.backend_process.returncode
            self.log("WARN", f"Backend process exited with code {retcode}")
            self.backend_process = None
            return self.start_backend()
        
        # Check health endpoint
        if not self.is_backend_healthy():
            self.log("WARN", "Backend health check failed")
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=3)
            except:
                self.backend_process.kill()
            self.backend_process = None
            return self.start_backend()
        
        return True
    
    def run(self):
        """Main watchdog loop."""
        self.log("INFO", "🐕 Backend Watchdog started")
        self.log("INFO", f"Check interval: {self.check_interval}s")
        
        # Initial startup
        self.start_backend()
        
        try:
            while self.running:
                time.sleep(self.check_interval)
                self.check_backend()
                
        except KeyboardInterrupt:
            self.log("INFO", "Keyboard interrupt received")
        finally:
            self.log("INFO", "Watchdog terminating")
            if self.backend_process:
                try:
                    self.backend_process.terminate()
                    self.backend_process.wait(timeout=5)
                except:
                    pass

if __name__ == "__main__":
    watchdog = BackendWatchdog()
    watchdog.run()
