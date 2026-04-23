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

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Vision LLM 서버가 가동 중입니다!"}

@app.post("/api/vision/analyze")
async def analyze_image(image_file: UploadFile = File(...)):
    print("이미지를 받았습니다.")
    # 1. 안드로이드에서 보낸 사진을 읽어서 Base64로 변환합니다.
    image_bytes = await image_file.read()
    encoded_image = base64.b64encode(image_bytes).decode('utf-8')    
    # 2. Ollama(moondream)에게 사진 분석을 요청합니다.
    # 팁: 뉴스 검색이 잘 되도록 단어 1개만 명사로 뽑아달라고 요청합니다.
    payload = {
        "model": "moondream", 
        "prompt": "이 사진에서 가장 잘 보이는 사물이나 주제를 한국어 단어 1개로만 말해줘. (예: 자동차, 인공지능, 커피, 날씨)",
        "images": [encoded_image], 
        "stream": False 
    }
    
    try:
        ollama_res = requests.post(OLLAMA_URL, json=payload)
        # AI가 뽑아낸 단어 (예: "자동차")
        keyword = ollama_res.json().get("response", "").strip()
        
        # 3. [핵심] 뽑아낸 키워드로 뉴스 DB에서 관련 기사 검색!
        db = SessionLocal()
        try:
            # 제목(title)이나 본문(content_raw)에 해당 키워드가 포함된 뉴스를 최신순으로 3개 가져옵니다.
            # (ILIKE를 써서 대소문자 구분 없이 검색합니다)
            search_query = f"%{keyword}%"
            related_news = db.query(News).filter(
                (News.title.ilike(search_query)) | (News.content_raw.ilike(search_query))
            ).order_by(News.id.desc()).limit(3).all()
            
            return {
                "success": True,
                "detected_object": keyword,
                "recommended_news": [
                    {
                        "id": n.id,
                        "title": n.title,
                        "link": n.url,
                        "preview": n.content_raw[:100] + "..." # 본문은 앞부분만 살짝!
                    } for n in related_news
                ]
            }
        finally:
            db.close() # DB 연결 종료
            
    except Exception as e:
        return {"success": False, "error": str(e)}
