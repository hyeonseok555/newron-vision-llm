# Newron News Audio Service

현재 나는 뉴스 오디오 제공 서비스 앱을 만들고 있어. 이 프로젝트는 백엔드의 **News RAG System**과 프론트엔드의 **Newron Android Piper TTS** 앱으로 구성되어 있습니다.

---

## 🧠 News RAG System (Multi-Model News Q&A API)

LLM(Gemma 4, Qwen 3.5, HyperCLOVA X 등)을 활용하여 뉴스 데이터를 기반으로 논리적이고 정확한 답변을 제공하는 검색 증강 생성(RAG) 시스템입니다. 현재 프로젝트에 적용하여 사용할 모델은 **EXAONE 3.5 7.8B** 모델입니다.

### 🚀 주요 특징
* **33+ 다양한 모델 지원**: 성능과 목적에 따라 Gemma 4, Qwen 3.5, Naver HyperCLOVA X SEED 등 다양한 모델을 즉시 전환하여 테스트 가능.
* **실시간 스트리밍 응답**: FastAPI 및 Server-Sent Events(SSE)를 사용하여 AI의 답변 과정을 실시간으로 확인 가능.
* **통합 모니터링 시스템**: `monitor.py`를 통해 GPU VRAM 사용량 및 33개 모델 컨테이너의 접속 현황을 한눈에 파악.
* **고성능 검색 (RAG)**: PostgreSQL 기반의 기사 본문 검색 및 인메모리 캐싱(NEWS_CACHE)을 통해 DB 부하를 최소화하고 응답 속도 극대화.
* **멀티턴(Multi-turn) 대화**: 대화 이력(History) 전달을 통해 이전 맥락을 유지하며 질문 가능.

### 🛠 기술 스택
* **Backend**: FastAPI (Python 3.9+)
* **LLM Engine**: Ollama (GPU 가속 지원)
* **Database**: PostgreSQL (psycopg2)
* **Monitoring**: Python threading & Docker log streaming
* **Infrastructure**: Docker & Docker Compose

### 📁 프로젝트 구조
```text
.
├── service/
│   ├── server.py             # 메인 백엔드 API 서버 (RAG 로직)
│   ├── monitor.py            # 통합 실시간 모니터링 도구
│   ├── client.py             # 테스트용 파이썬 클라이언트
│   ├── docker-compose.yml    # 33개 모델 및 인프라 통합 설정
│   ├── Dockerfile            # API 서버 이미지 정의
│   ├── docs/                 # 아키텍처 다이어그램 (PUML, PNG)
│   └── reports/              # 테스트 및 벤치마크 결과 레포트
├── manage_tunnel.sh          # 클라우드플레어 터널링 관리 스크립트
└── 가상화 활성화 명령어.txt    # 초기 환경 설정 가이드
```

---

## 🎙️ Newron Android Piper TTS

본 프로젝트는 고성능 음성 합성(TTS) 엔진인 Sherpa-ONNX와 Piper VITS 모델을 활용하여 실시간 뉴스를 자연스러운 인간의 목소리로 읽어주는 안드로이드 애플리케이션입니다.

### 🚀 주요 기능
* **실시간 뉴스 오디오 제공**: 서버로부터 최신 뉴스 기사를 카테고리별로 수신하여 제공합니다.
* **음성 합성**: VITS(Variational Inference with adversarial learning for end-to-End Text-to-Speech) 모델을 통해 기계음이 아닌 자연스러운 아나운서 음성을 생성합니다.
* **백그라운드 지속 재생**: Media3 Session을 통해 앱이 백그라운드에 있거나 화면이 꺼진 상태에서도 끊김 없는 뉴스 청취가 가능합니다.
* **UI/UX**: Shimmer 효과와 Lottie 애니메이션을 활용하여 사용자에게 시각적으로 즐거운 경험을 제공합니다.

### 🛠 기술 스택
**전면부 (Frontend)**
* **언어**: Kotlin
* **UI 프레임워크**: Jetpack Compose (Material 3)
* **이미지/애니메이션**: Lottie Compose, Shimmer Compose

**음성 및 미디어 (Audio & Media)**
* **TTS 엔진**: Sherpa-ONNX (C++ Native)
* **AI 모델**: Piper VITS ONNX (v9_epoch296.onnx 등)
* **미디어 프레임워크**: AndroidX Media3 (ExoPlayer, MediaSession)

**통신 및 배포 (Networking & Deployment)**
* **네트워크**: Retrofit2, OkHttp3, Gson
* **모델 관리**: Git LFS (대용량 모델 관리 권장)

### 🏗 아키텍처 설계
본 앱은 단일 활동(Single Activity) 패턴과 전속 서비스(Foreground Service) 구조를 결합하여 견고한 미디어 재생 환경을 구축했습니다. (Bass et al., 2012)

* **MainActivity**: Jetpack Compose를 통한 선언적 UI 관리 및 사용자와의 상호작용 담당.
* **TTSService**: Media3 MediaSessionService를 상속받아 시스템 전체에서 미디어 상태를 동기화하고 잠금 화면 제어를 지원합니다.
* **SherpaOnnxTTS**: JNI(Java Native Interface)를 통해 C++ 네이티브 AI 엔진과 통신하여 실시간 오디오 데이터를 생성합니다.
