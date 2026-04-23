import requests
import re
import os
import time
import sys
import threading
import itertools
import subprocess
import json
from datetime import datetime

# 서버 버전별 포트 설정 (Vision 모델들)
API_VERSIONS = {
    "1": {"name": "Moondream (7000번)", "url": "http://127.0.0.1:7000/api/vision/analyze"},
    "2": {"name": "Llama 3.2 Vision (7001번)", "url": "http://127.0.0.1:7001/api/vision/analyze"},
    "3": {"name": "MiniCPM-V (7002번)", "url": "http://127.0.0.1:7002/api/vision/analyze"},
    "4": {"name": "LLaVA-Phi3 (7003번)", "url": "http://127.0.0.1:7003/api/vision/analyze"},
    "5": {"name": "BakLLaVA (7004번)", "url": "http://127.0.0.1:7004/api/vision/analyze"},
    "6": {"name": "LLaVA v1.6 (7005번)", "url": "http://127.0.0.1:7005/api/vision/analyze"},
}

REPORT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports", "vision_test_report.md")

def get_gpu_info():
    """ nvidia-smi를 호출하여 GPU 사용률과 메모리 정보를 가져옵니다. """
    try:
        cmd = "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits"
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        util, used, total = output.split(',')
        return int(util.strip()), f"MEM: {used.strip()}/{total.strip()}MiB"
    except:
        return 0, "GPU 정보 확인 불가"

def save_to_report(version_name, image_path, detected_object, news_count, elapsed_time, gpu_info):
    """ 테스트 결과를 리포트의 요약 표와 상세 로그 섹션에 각각 저장합니다. """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 상세 로그 항목 생성
    new_log_entry = f"""
### 🕒 테스트 일시: {now}
- **모델 버전:** {version_name}
- **테스트 이미지:** {image_path}
- **소요 시간:** {elapsed_time:.2f}초
- **최종 GPU 상태:** {gpu_info}
- **추출된 키워드:** {detected_object}
- **추천 뉴스 개수:** {news_count}건
---
"""
    try:
        os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
        if not os.path.exists(REPORT_FILE):
            with open(REPORT_FILE, "w", encoding="utf-8") as f:
                f.write("# 👁️ Vision RAG 테스트 결과 보고서\n\n## 📊 테스트 요약표\n| No. | 테스트 일시 | 모델 버전 | 이미지 경로 | 추출 키워드 | 추천 뉴스 | 소요 시간 | GPU MEM |\n|:---:|:---|:---|:---|:---|:---:|:---:|:---|\n\n---\n\n## 📝 상세 테스트 로그\n")
        
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. 신규 번호(No.) 계산
        all_nos = re.findall(r"\| (\d+) \| \d{4}-\d{2}-\d{2}", content)
        next_no = max([int(n) for n in all_nos]) + 1 if all_nos else 1
        
        # 2. 표에 행 삽입 (구분선 |:---:| 바로 아래)
        new_row = f"| {next_no} | {now} | {version_name} | {os.path.basename(image_path)} | {detected_object} | {news_count}건 | {elapsed_time:.2f}s | {gpu_info} |"
        table_sep = "|:---:|:---|:---|:---|:---|:---:|:---:|:---|"
        table_insert_pos = content.find(table_sep)
        if table_insert_pos != -1:
            line_end = content.find("\n", table_insert_pos) + 1
            content = content[:line_end] + new_row + "\n" + content[line_end:]
        
        # 3. 상세 로그 섹션에 추가
        log_section_marker = "## 📝 상세 테스트 로그"
        log_pos = content.find(log_section_marker)
        if log_pos != -1:
            log_insert_pos = log_pos + len(log_section_marker) + 1
            content = content[:log_insert_pos] + new_log_entry + content[log_insert_pos:]
        else:
            content += new_log_entry

        with open(REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"⚠️ 리포트 저장 실패: {e}")
        return False

def loading_animation(stop_event, start_time):
    """ GPU 상태 변화를 감지하고 로그를 남기며 애니메이션을 표시합니다. """
    chars = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    last_util = -1
    
    print("\n[AI 비전 분석 시작]")
    
    while not stop_event.is_set():
        current_util, mem_info = get_gpu_info()
        elapsed = time.time() - start_time
        
        if current_util != last_util and current_util > 0:
            log_msg = f"[{elapsed:6.1f}s] GPU 사용률 변경: {last_util}% -> {current_util}% ({mem_info})"
            sys.stdout.write(f"\r{log_msg}                           \n")
            last_util = current_util
            
        status_line = f"\r[이미지 분석 중...] {next(chars)}  Time: {elapsed:.1f}s | GPU: {current_util}% | {mem_info} "
        sys.stdout.write(status_line)
        sys.stdout.flush()
        time.sleep(0.5)

def test_vision_model():
    print("=" * 60)
    print("👁️ 뉴론 Vision RAG 멀티 모델 테스트 클라이언트")
    print("=" * 60)
    
    print("\n테스트할 버전을 선택하세요:")
    for key, info in API_VERSIONS.items():
        print(f"[{key}] {info['name']}")
    
    version_choice = input("\n선택 (기본값 1): ").strip() or "1"
    if version_choice not in API_VERSIONS:
        print("❌ 잘못된 선택입니다. 프로그램을 종료합니다.")
        return
    
    selected_version = API_VERSIONS[version_choice]
    API_URL = selected_version['url']
    print(f"👉 선택됨: {selected_version['name']}\n")

    while True:
        target_path = input("\n분석할 이미지 파일 또는 폴더 경로를 입력하세요 (종료: exit)\n예: /hdd4/newron-vision-llm/testimg\n입력: ").strip()
        if target_path.lower() in ['exit', 'quit']:
            break
            
        if not os.path.exists(target_path):
            print("❌ 오류: 해당 경로가 존재하지 않습니다. 경로를 다시 확인해주세요.")
            continue

        # 파일인지 폴더인지 구분하여 처리할 이미지 목록 생성
        if os.path.isdir(target_path):
            image_files = sorted([os.path.join(target_path, f) for f in os.listdir(target_path) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.webp'))])
            if not image_files:
                print("❌ 오류: 폴더 내에 이미지 파일(.jpg, .png 등)이 없습니다.")
                continue
            print(f"\n📂 폴더 내 총 {len(image_files)}개의 이미지 파일을 순차적으로 분석합니다.")
        else:
            image_files = [target_path]

        total_files = len(image_files)
        
        # 파일 개수만큼 반복문 실행
        for idx, image_path in enumerate(image_files, 1):
            print(f"\n[{idx}/{total_files}] 📡 {API_URL} 로 이미지 전송 중... ({os.path.basename(image_path)})")
            
            start_time = time.time()
            stop_event = threading.Event()
            loader = threading.Thread(target=loading_animation, args=(stop_event, start_time))
            loader.start()

            try:
                with open(image_path, 'rb') as f:
                    files = {'image_file': f}
                    # 스트리밍 모드로 비전 API 전송
                    response = requests.post(API_URL, files=files, stream=True, timeout=300)
                
                print("\n" + "=" * 50)
                print(f"🚀 [{idx}/{total_files}] 서버 작업 실시간 중계")
                print("=" * 50)
                
                if response.status_code == 200:
                    final_result = None
                    
                    # 서버가 보내주는 텍스트(JSON)를 한 줄씩 실시간으로 받아서 출력
                    for line in response.iter_lines():
                        if line:
                            data = json.loads(line.decode('utf-8'))
                            step = data.get("step")
                            
                            if step == 100:
                                # 100번은 최종 결과 데이터
                                final_result = data.get("result")
                            elif step == -1:
                                # -1번은 에러 발생
                                print(data.get("message"))
                                break
                            else:
                                # 1~5단계 진행 상황 출력
                                print(data.get("message"))
                                
                    stop_event.set()
                    loader.join()
                    elapsed = time.time() - start_time
                    _, gpu_final = get_gpu_info()
                    
                    print("\n" + "-" * 60)
                    if final_result and final_result.get("success"):
                        keyword = final_result.get("detected_object", "결과 없음")
                        news_list = final_result.get("recommended_news", [])
                        
                        print(f"✅ 분석 최종 성공! (소요 시간: {elapsed:.2f}초)")
                        print(f"🎯 AI가 추출한 키워드: [{keyword}]")
                        print(f"📰 추천된 뉴스 기사 ({len(news_list)}건):")
                        for news_idx, news in enumerate(news_list):
                            print(f"   {news_idx+1}. {news.get('title')}")
                        
                        # 리포트에 저장
                        save_to_report(selected_version['name'], image_path, keyword, len(news_list), elapsed, gpu_final)
                        print(f"\n📝 테스트 결과가 요약표(reports/vision_test_report.md)에 저장되었습니다.")
                    else:
                        err_msg = final_result.get('error') if final_result else (data.get('error') if data else '알 수 없는 에러')
                        print(f"❌ 분석 실패: {err_msg}")
                else:
                    stop_event.set()
                    loader.join()
                    print(f"❌ 서버 응답 오류 ({response.status_code}): {response.text}")
                    
                print("-" * 60)
                
            except Exception as e:
                stop_event.set()
                loader.join()
                print(f"\n❌ 클라이언트 통신 오류: {e}")
            
            # 다음 파일로 넘어가기 전에 잠시 대기 (서버 과부하 방지)
            if idx < total_files:
                time.sleep(1)

if __name__ == "__main__":
    test_vision_model()
