#!/bin/bash
# 웹 대시보드 필수 패키지 설치 스크립트

echo "=========================================="
echo "🌐 SmartFarm 웹 대시보드 패키지 설치"
echo "=========================================="
echo ""

# Flask-CORS가 이미 설치되어 있는지 확인
if python3 -c "import flask_cors" 2>/dev/null; then
    echo "✅ Flask-CORS 이미 설치되어 있습니다."
else
    echo "[1/2] Flask-CORS 설치 중..."
    echo "  → apt를 통해 시스템 패키지로 설치합니다..."
    
    # sudo 권한 필요 여부 확인
    if [ "$EUID" -eq 0 ]; then
        apt update && apt install -y python3-flask-cors
    else
        sudo apt update && sudo apt install -y python3-flask-cors
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ Flask-CORS 설치 완료"
    else
        echo "❌ Flask-CORS 설치 실패"
        echo ""
        echo "대안: pip를 사용하여 설치하려면 다음 명령을 실행하세요:"
        echo "  python3 -m pip install --break-system-packages flask-cors"
        exit 1
    fi
fi
echo ""

echo "[2/2] 설치 확인 중..."
python3 -c "import flask; print('✅ Flask:', flask.__version__)" 2>/dev/null || echo "❌ Flask 없음"
python3 -c "import flask_cors; print('✅ Flask-CORS: OK')" 2>/dev/null || echo "❌ Flask-CORS 없음"
echo ""

echo "=========================================="
echo "✅ 패키지 설치 완료!"
echo "=========================================="
echo ""
echo "웹 서버 실행:"
echo "  python3 web_server.py"
echo ""
echo "자세한 설정은 WEB_DASHBOARD_SETUP.md 참고"

