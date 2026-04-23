import subprocess
import re
import sys
import os
import signal
import threading
import requests
import time
from datetime import datetime

# --- Plain Text Version (No ANSI Codes) ---
# All colors removed to ensure 100% compatibility with any terminal.

# Container Configuration
CONTAINERS = {
    "vision_api": "[Vision RAG API Server]"
}

# Ollama API URL
OLLAMA_API_URL = "http://localhost:11434/api/ps"

def get_gpu_models():
    """Get models currently loaded in GPU VRAM via Ollama API."""
    try:
        response = requests.get(OLLAMA_API_URL, timeout=2)
        if response.status_code == 200:
            return response.json().get("models", [])
        return []
    except:
        return []

def display_gpu_status_loop():
    """Loop to detect and print GPU model load/unload events."""
    prev_model_names = set()

    while True:
        models = get_gpu_models()
        curr_model_names = {m['name'] for m in models}

        newly_loaded = curr_model_names - prev_model_names
        newly_unloaded = prev_model_names - curr_model_names

        now = datetime.now().strftime("%H:%M:%S")

        if newly_loaded:
            for model_name in newly_loaded:
                model_info = next((m for m in models if m['name'] == model_name), {})
                size_gb = model_info.get('size', 0) / (1024**3)
                vram_gb = model_info.get('size_vram', 0) / (1024**3)
                print(f"\n[LOADED] [{now}] Model: {model_name}")
                print(f"   Size: {size_gb:.2f}GB | VRAM: {vram_gb:.2f}GB")
                print("-" * 55)
                sys.stdout.flush()

        if newly_unloaded:
            for model_name in newly_unloaded:
                print(f"\n[UNLOADED] [{now}] Model: {model_name}")
                print("-" * 55)
                sys.stdout.flush()

        prev_model_names = curr_model_names
        time.sleep(10)

def log_reader(container_name, label):
    """Real-time detection of image analysis requests."""
    try:
        cmd = ["sudo", "docker", "logs", "-f", "--tail", "0", container_name]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            
            if "POST /api/vision/analyze" in line:
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                ip = ip_match.group(1) if ip_match else "Unknown"
                
                print(f"\n[ACCESS] [{datetime.now().strftime('%H:%M:%S')}] {label}")
                print(f"   Client IP: {ip}")
                print("-" * 55)
                sys.stdout.flush()
                
    except Exception as e:
        pass

def monitor_logs():
    print("\n" + "=" * 55)
    print("News RAG Integrated Monitoring Desk")
    print("=" * 55)
    print(f"  - Target: vision_api (Image Analysis)")
    print(f"  - GPU   : moondream status (10s interval)")
    print("  - Press Ctrl+C to exit.\n")

    gpu_thread = threading.Thread(target=display_gpu_status_loop, daemon=True)
    gpu_thread.start()

    threads = []
    for name, label in CONTAINERS.items():
        t = threading.Thread(target=log_reader, args=(name, label), daemon=True)
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nClosing monitoring safely.")
        sys.exit(0)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Error: sudo required for docker logs.")
        print("Usage: sudo python3 monitor.py")
        sys.exit(1)
        
    monitor_logs()
