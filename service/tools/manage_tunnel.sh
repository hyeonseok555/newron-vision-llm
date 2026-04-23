#!/bin/bash

# --- 설정 정보 ---
REMOTE_USER="hs"
REMOTE_HOST="220.75.212.41"
REMOTE_PORT="4545"
LOCAL_PORT="4546"

# 1. 현재 4546 포트가 살아있는지 확인 (lsof 이용)
if ! lsof -i :$LOCAL_PORT > /dev/null; then
    echo "[$(date)] ⚠️ 터널이 끊어져 있습니다. 재연결을 시도합니다..."
    
    # 2. 끊어진 좀비 프로세스가 있을 수 있으니 깔끔하게 정리
    pkill -f "L $LOCAL_PORT:127.0.0.1:$LOCAL_PORT"
    
    # 3. 터널 연결 실행 (Keep-Alive 옵션 추가)
    ssh -p $REMOTE_PORT -N -f -L $LOCAL_PORT:127.0.0.1:$LOCAL_PORT $REMOTE_USER@$REMOTE_HOST \
        -o ServerAliveInterval=60 \
        -o ServerAliveCountMax=3
    
    if [ $? -eq 0 ]; then
        echo "✅ 터널 연결 성공!"
    else
        echo "❌ 연결 실패. 네트워크나 서버 상태를 확인하세요."
    fi
else
    echo "[$(date)] 🟢 터널이 정상적으로 작동 중입니다."
fi
