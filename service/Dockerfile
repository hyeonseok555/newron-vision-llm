# 파이썬 3.9 버전이 미리 설치된 가벼운 리눅스(slim) 이미지를 다운로드하여 기본 뼈대로 삼습니다.
FROM python:3.9-slim

# 컨테이너 내부에서 우리가 앞으로 작업할 기본 폴더 경로를 '/app'으로 지정합니다. (cd /app 과 같은 효과)
WORKDIR /app

# 내 컴퓨터에 있는 'requirements.txt' 파일을 컨테이너 내부의 '/app' 폴더 안으로 복사해 넣습니다.
COPY requirements.txt .

# 복사해 온 목록 파일(requirements.txt)을 보고, 파이썬 패키지 관리자(pip)를 시켜서 필요한 라이브러리들을 싹 다 설치합니다.
# (--no-cache-dir은 설치 후 남는 찌꺼기 파일을 지워서 용량을 아끼는 옵션입니다.)
RUN pip install --no-cache-dir -r requirements.txt

# 내 컴퓨터의 'service' 폴더 안에 있는 나머지 모든 소스 코드 파일(server.py 등)을 컨테이너 안으로 전부 복사합니다.
COPY . .

# 도커 컨테이너가 최종적으로 켜질 때 딱 한 번 실행할 메인 명령어입니다. 
# uvicorn 서버를 이용해 server.py 안의 'app'을 실행하고, 0.0.0.0(모든 IP 허용) 주소와 8000번 포트로 엽니다. 
# (--reload 옵션을 주면 코드를 수정할 때마다 서버가 자동으로 껐다 켜집니다.)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7000", "--reload"]
