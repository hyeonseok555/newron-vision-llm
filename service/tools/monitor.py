import subprocess
import re
import sys
import os
import signal
import threading
import requests
import time
from datetime import datetime

# --- 프리미엄 컬러 한글 대시보드 버전 ---
G = "\033[92m" # 초록 (성공)
B = "\033[94m" # 파랑 (정보)
C = "\033[96m" # 청록 (구분선)
Y = "\033[93m" # 노랑 (경고)
R = "\033[91m" # 빨강 (에러)
BOLD = "\033[1m"
RESET = "\033[0m"

# gpu 모델 이름 가져오기
gpu_name = subprocess.check_output("nvidia-smi --query-gpu=name --format=csv,noheader", shell=True).decode('utf-8').strip()

# 컨테이너 설정
CONTAINERS = {
    "vision_api": "[7000번] 무림(Moondream)",
    "api_llama": "[7001번] 라마 3.2 Vision",
    "api_minicpm": "[7002번] 미니CPM-V",
    "api_phi3": "[7003번] LLaVA-Phi3",
    "api_bakllava": "[7004번] BakLLaVA",
    "api_llava_v16": "[7005번] LLaVA v1.6"
}

# Ollama API 주소
OLLAMA_API_URL = "http://localhost:11434/api/ps"

def get_gpu_info():
    """ nvidia-smi를 통해 GPU 사용률, 메모리, 온도를 가져옵니다. """
    try:
        cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits"
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        util, used, total, temp = output.split(',')
        return {
            "util": util.strip(),
            "used": used.strip(),
            "total": total.strip(),
            "temp": temp.strip()
        }
    except:
        return None

def get_gpu_models():
    """Ollama API를 통해 VRAM에 로드된 모델 목록을 가져옵니다."""
    try:
        response = requests.get(OLLAMA_API_URL, timeout=2)
        return response.json().get("models", []) if response.status_code == 200 else []
    except:
        return []

def display_gpu_status_loop():
    """GPU 상태 및 모델 변화를 실시간으로 감지합니다."""
    prev_model_names = set()
    tick = 0

    while True:
        models = get_gpu_models()
        curr_model_names = {m['name'] for m in models}
        newly_loaded = curr_model_names - prev_model_names
        newly_unloaded = prev_model_names - curr_model_names
        now = datetime.now().strftime("%H:%M:%S")
        gpu = get_gpu_info()

        if gpu:
            # 사용률이 높으면 노란색으로 경고
            u_color = Y if int(gpu['util']) > 80 else G
            gpu_str = f"{u_color}사용률 {gpu['util']}%{RESET} | {Y}메모리 {gpu['used']}/{gpu['total']} MB{RESET} | {R}온도 {gpu['temp']}°C{RESET}"
        else:
            gpu_str = f"{R}GPU 상태 확인 불가{RESET}"

        if newly_loaded:
            for m_name in newly_loaded:
                m_info = next((m for m in models if m['name'] == m_name), {})
                vram = m_info.get('size_vram', 0) / (1024**3)
                print(f"\n{B}{BOLD}[모델 로드됨]{RESET} {C}{m_name}{RESET} (VRAM: {vram:.1f}GB)")
                print(f"   {BOLD}현재 시스템 상태:{RESET} {gpu_str}")
                print(f"{C}{'-' * 60}{RESET}")

        if newly_unloaded:
            for m_name in newly_unloaded:
                print(f"\n{Y}{BOLD}[모델 해제됨]{RESET} {C}{m_name}{RESET}")
                print(f"   {BOLD}현재 시스템 상태:{RESET} {gpu_str}")
                print(f"{C}{'-' * 60}{RESET}")

        # 30초마다 헬스체크(상태 점검) 출력
        if tick % 3 == 0 and not newly_loaded and not newly_unloaded:
            print(f"{BOLD}[정기 상태 점검]{RESET} [{now}] {gpu_str}")
            sys.stdout.flush()

        prev_model_names = curr_model_names
        tick += 1
        time.sleep(10)

def log_reader(container_name, label):
    """도커 로그를 읽어 실시간 요청과 키워드를 감지합니다."""
    try:
        cmd = ["sudo", "docker", "logs", "-f", "--tail", "0", container_name]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        while True:
            line = process.stdout.readline()
            if not line: break
            
            # 1. API 분석 요청 감지
            if "POST /api/vision/analyze" in line:
                ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                ip = ip_match.group(1) if ip_match else "알 수 없음"
                gpu = get_gpu_info()
                gpu_sum = f"{gpu['util']}% / {gpu['temp']}°C" if gpu else "확인불가"
                
                print(f"\n{G}{BOLD}[분석 요청 감지]{RESET} {B}{label}{RESET}")
                print(f"   {BOLD}클라이언트 IP:{RESET} {ip} | {BOLD}GPU 상태:{RESET} {Y}{gpu_sum}{RESET}")
                sys.stdout.flush()

            # 2. AI가 추출한 키워드 감지
            if "[AI-KEYWORD]" in line:
                keyword = line.split("[AI-KEYWORD]")[-1].strip()
                print(f"   {G}{BOLD}AI 추출 키워드:{RESET} {Y}{keyword}{RESET}")
                print(f"{G}{'-' * 60}{RESET}")
                sys.stdout.flush()

    except:
        pass

def monitor_logs():
    os.system('clear')
    print(f"{C}{'=' * 65}{RESET}")
    print(f"{C}{BOLD}      🚀 뉴론 비전 RAG 통합 모니터링 데스크 (PREMIUM){RESET}")
    print(f"{C}{'=' * 65}{RESET}")
    print(f"  {BOLD}현재 상태:{RESET} {G}정상 작동 중{RESET} | {BOLD}감시 대상:{RESET} 비전 모델 6종 (7000-7005)")
    print(f"  {BOLD}GPU 측정:{RESET} 사용률, 메모리, 온도 실시간 추적 중 (10초 간격)")
    print(f"  {BOLD}GPU 모델:{RESET} {gpu_name}")
    print(f"  {BOLD}실시간 분석:{RESET} 모델 로딩 상태 및 AI 추출 키워드 중계 중")
    
    print(f"{C}{'=' * 65}{RESET}\n")

    # 배경 스레드 시작
    threading.Thread(target=display_gpu_status_loop, daemon=True).start()
    for name, label in CONTAINERS.items():
        threading.Thread(target=log_reader, args=(name, label), daemon=True).start()

    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{R}모니터링이 사용자에 의해 종료되었습니다.{RESET}")
        sys.exit(0)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print(f"{R}오류: 도커 로그를 읽기 위해 sudo 권한이 필요합니다.{RESET}")
        sys.exit(1)
    monitor_logs()
