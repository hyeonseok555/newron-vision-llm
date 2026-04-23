import os
import base64
import requests
from fastapi import FastAPI, UploadFile, File

# DB 연결을 위한 도구들입니다.
from sqlalchemy import create_engine, Column, Integer, String, Text, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI(title="뉴론 Vision LLM API")

# --- [DB 설정 구역] ---
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

# 실제 DB의 news 테이블 구조와 똑같이 매핑합니다.
class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)        # 뉴스 제목
    content_raw = Column(Text, nullable=False)  # 뉴스 본문
    url = Column(Text)                          # 뉴스 원문 링크
# --- [DB 설정 끝] ---

# Ollama 서버 주소
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
        db = SessionLocal()
        try:
            # [단계 1] 이미지 수신
            yield json.dumps({"step": 1, "message": f"📸 [단계 1] 이미지를 성공적으로 수신했습니다. (사용 모델: {MODEL_NAME})"}) + "\n"
            await asyncio.sleep(0.1)
            
            image_bytes = await image_file.read()
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')    
            
            # [단계 2] AI 분석 요청
            yield json.dumps({"step": 2, "message": "🧠 [단계 2] AI 비전 모델이 이미지 속 사물을 추론하고 있습니다..."}) + "\n"
            
            payload = {
                "model": MODEL_NAME, 
                "system": "너는 이미지에서 가장 핵심적인 사물의 이름 딱 3개(한국어 명사)만 대답하는 봇이야. 인사말, 부가적인 설명, 마크다운 기호(*, ` 등)는 절대 쓰지 마.",
                "prompt": "이 사진에서 가장 잘 보이는 사물을 한국어 명사 3개로 대답해.",
                "images": [encoded_image], 
                "stream": False 
            }
            
            ollama_res = requests.post(OLLAMA_URL, json=payload, timeout=300)
            raw_response = ollama_res.json().get("response", "").strip()
            
            # [핵심 필터링] 3개 단어 추출
            import re
            clean_text = re.sub(r'[*`_,\.]', '', raw_response)
            keywords = [w.strip() for w in clean_text.split() if w.strip()][:3]
            keywords_str = ", ".join(keywords)
            
            # [단계 3] AI 분석 완료
            yield json.dumps({"step": 3, "message": f"🎯 [단계 3] AI 분석 완료! 추출된 핵심 단어: [{keywords_str}] (원문: {raw_response[:20]}...)"}) + "\n"
            print(f"[AI-KEYWORD] {keywords_str}") 
            await asyncio.sleep(0.5)

            # [단계 4 & 5] DB 연결 및 검색
            related_news = []
            is_valid_keywords = keywords and "알수없음" not in keywords
            
            if is_valid_keywords:
                yield json.dumps({"step": 4, "message": f"🔍 [단계 4] DB 서버에 연결하여 '{keywords_str}' 관련 뉴스를 검색합니다..."}) + "\n"
                try:
                    conditions = []
                    for kw in keywords:
                        search_query = f"%{kw}%"
                        conditions.append(News.title.ilike(search_query))
                        conditions.append(News.content_raw.ilike(search_query))
                    
                    related_news = db.query(News).filter(or_(*conditions)).order_by(News.id.desc()).limit(3).all()
                    yield json.dumps({"step": 5, "message": "📥 [단계 5] 처리 완료! 최종 결과를 반환합니다."}) + "\n"
                except Exception as db_err:
                    print(f"DB 검색 오류: {db_err}")
            else:
                yield json.dumps({"step": 4, "message": "⚠️ [건너뜀] 유효한 키워드가 없어 DB 검색 및 결과 수신을 중단합니다."}) + "\n"
            
            final_result = {
                "success": True,
                "detected_object": keywords_str if is_valid_keywords else "추출 실패",
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
                
        except Exception as outer_err:
            yield json.dumps({"step": -1, "error": str(outer_err), "message": f"❌ [오류 발생] {str(outer_err)}"}) + "\n"
        finally:
            db.close()
            
    return StreamingResponse(generate_progress(), media_type="text/event-stream")
