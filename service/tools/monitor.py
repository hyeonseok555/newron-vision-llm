import subprocess
import re
import sys
import os
import signal
import threading
import requests
import time
from datetime import datetime

# --- 일반 텍스트 버전 (ANSI 색상 코드 없음) ---
# 모든 터미널과의 호환성을 위해 색상 코드를 제거했습니다.

# 컨테이너 설정
CONTAINERS = {
    "vision_api": "[7000번] Moondream",
    "api_llama": "[7001번] Llama 3.2",
    "api_minicpm": "[7002번] MiniCPM-V",
    "api_phi3": "[7003번] LLaVA-Phi3",
    "api_bakllava": "[7004번] BakLLaVA",
    "api_llava_v16": "[7005번] LLaVA v1.6"
}

# Ollama API 주소
OLLAMA_API_URL = "http://localhost:11434/api/ps"

def get_gpu_models():
    """Ollama API를 통해 현재 GPU VRAM에 로드된 모델 목록을 가져옵니다."""
    try:
        response = requests.get(OLLAMA_API_URL, timeout=2)
        if response.status_code == 200:
            return response.json().get("models", [])
        return []
    except:
        return []

def display_gpu_status_loop():
    """GPU 모델 로드/언로드 이벤트를 감지하고 출력하는 루프입니다."""
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
                print(f"\n[모델 로드됨] [{now}] 모델명: {model_name}")
                print(f"   크기: {size_gb:.2f}GB | VRAM 점유: {vram_gb:.2f}GB")
                print("-" * 55)
                sys.stdout.flush()

        if newly_unloaded:
            for model_name in newly_unloaded:
                print(f"\n[모델 해제됨] [{now}] 모델명: {model_name}")
                print("-" * 55)
                sys.stdout.flush()

        prev_model_names = curr_model_names
        time.sleep(10)

def log_reader(container_name, label):
    """이미지 분석 요청을 실시간으로 감지합니다."""
    try:
        cmd = ["sudo", "docker", "logs", "-f", "--tail", "0", container_name]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        while True:
            line = process.stdout.readline()
            if not line:
                break
            
            if "POST /api/vision/analyze" in line:
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                ip = ip_match.group(1) if ip_match else "알 수 없음"
                
                print(f"\n[접속 감지] [{datetime.now().strftime('%H:%M:%S')}] {label}")
                print(f"   클라이언트 IP: {ip}")
                print("-" * 55)
                sys.stdout.flush()
                
    except Exception as e:
        pass

def monitor_logs():
    print("\n" + "=" * 55)
    print("뉴스 RAG 통합 모니터링 데스크 (멀티 모델 모드)")
    print("=" * 55)
    print(f"  - 대상: 포트 7000 ~ 7005 (모든 Vision API)")
    print(f"  - GPU : 모든 로드된 모델 실시간 감지 (10초 간격)")
    print("  - 종료하려면 Ctrl+C를 누르세요.\n")

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
        print("\n모니터링을 안전하게 종료합니다.")
        sys.exit(0)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("오류: 도커 로그 접근을 위해 sudo 권한이 필요합니다.")
        print("사용법: sudo python3 monitor.py")
        sys.exit(1)
        
    monitor_logs()
