import os
import base64
import requests
from fastapi import FastAPI, UploadFile, File

# DB 연결을 위한 도구들입니다.
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI(title="뉴론 Vision LLM API")

# --- [DB 설정 구역] ---
# 도커 환경 변수에서 DB 정보를 가져옵니다. (우리가 Tailscale IP 넣었던 그 정보들입니다!)
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

# PostgreSQL 접속 주소 생성
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# DB 연결 엔진 및 세션 설정
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# [확인 완료!] 실제 DB의 news 테이블 구조와 똑같이 매핑합니다.
class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)        # 뉴스 제목
    content_raw = Column(Text, nullable=False)  # 뉴스 본문
    url = Column(Text)                          # 뉴스 원문 링크
# --- [DB 설정 끝] ---

# Ollama 서버 주소 (Host 모드이므로 127.0.0.1 사용)
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL_NAME = os.getenv("MODEL_NAME", "moondream")

from fastapi.responses import StreamingResponse
import json
import asyncio

@app.get("/")
def health_check():
    return {"status": "ok", "message": f"Vision LLM 서버({MODEL_NAME})가 가동 중입니다!"}

@app.post("/api/vision/analyze")
async def analyze_image(image_file: UploadFile = File(...)):
    async def generate_progress():
        try:
            # [단계 1] 이미지 수신
            yield json.dumps({"step": 1, "message": f"📸 [단계 1] 이미지를 성공적으로 수신했습니다. (사용 모델: {MODEL_NAME})"}) + "\n"
            await asyncio.sleep(0.1) # 화면에 보이게 살짝 딜레이
            
            image_bytes = await image_file.read()
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')    
            
            # [단계 2] AI 분석 요청
            yield json.dumps({"step": 2, "message": "🧠 [단계 2] AI 비전 모델이 이미지 속 사물을 추론하고 있습니다..."}) + "\n"
            
            payload = {
                "model": MODEL_NAME, 
                "system": "너는 이미지에서 가장 핵심적인 사물의 이름 딱 1개(한국어 명사)만 대답하는 봇이야. 인사말, 부가적인 설명, 마크다운 기호(*, ` 등)는 절대 쓰지 마.",
                "prompt": "이 사진에서 가장 잘 보이는 사물을 한국어 명사 1개로 대답해.",
                "images": [encoded_image], 
                "stream": False 
            }
            
            # Ollama API 동기 호출 (이 동안 대기)
            ollama_res = requests.post(OLLAMA_URL, json=payload, timeout=300)
            raw_response = ollama_res.json().get("response", "").strip()
            
            # [핵심 필터링] 마크다운 특수문자 제거 및 마지막 단어만 핀셋 추출
            import re
            clean_text = re.sub(r'[*`_,\.]', '', raw_response)
            words = clean_text.split()
            keyword = words[-1].strip() if words else "알수없음"
            
            # [단계 3] AI 분석 완료
            yield json.dumps({"step": 3, "message": f"🎯 [단계 3] AI 분석 완료! 추출된 핵심 단어: [{keyword}] (원문: {raw_response[:20]}...)"}) + "\n"
            await asyncio.sleep(0.5)

            # [단계 4] DB 연결 및 검색
            yield json.dumps({"step": 4, "message": f"🔍 [단계 4] DB 서버(127.0.0.1:4546)에 연결하여 '{keyword}' 관련 뉴스를 검색합니다..."}) + "\n"
            
            db = SessionLocal()
            try:
                search_query = f"%{keyword}%"
                related_news = db.query(News).filter(
                    (News.title.ilike(search_query)) | (News.content_raw.ilike(search_query))
                ).order_by(News.id.desc()).limit(3).all()
                
                # [단계 5] 최종 데이터 수신 완료
                yield json.dumps({"step": 5, "message": "📥 [단계 5] DB 데이터 수신 완료! 최종 결과를 반환합니다."}) + "\n"
                
                final_result = {
                    "success": True,
                    "detected_object": keyword,
                    "recommended_news": [
                        {
                            "id": n.id,
                            "title": n.title,
                            "link": n.url,
                            "preview": n.content_raw[:100] + "..."
                        } for n in related_news
                    ]
                }
                yield json.dumps({"step": 100, "result": final_result}) + "\n"
                
            finally:
                db.close()
                
        except Exception as e:
            yield json.dumps({"step": -1, "error": str(e), "message": f"❌ [오류 발생] {str(e)}"}) + "\n"

    return StreamingResponse(generate_progress(), media_type="application/x-ndjson")
