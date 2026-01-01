#!/bin/bash
# Arduino 라이브러리 설치 스크립트
# 사용법: bash install_arduino_libs.sh

echo "=========================================="
echo "🔧 Arduino 라이브러리 설치 시작"
echo "=========================================="
echo ""

# 라이브러리 인덱스 업데이트
echo "[1/4] 라이브러리 인덱스 업데이트 중..."
arduino-cli lib update-index
if [ $? -eq 0 ]; then
    echo "✅ 인덱스 업데이트 완료"
else
    echo "❌ 인덱스 업데이트 실패"
    exit 1
fi
echo ""

# Board A용 라이브러리 설치
echo "[2/4] Board A용 라이브러리 설치 중..."
echo "  - U8g2 설치 중..."
arduino-cli lib install "U8g2"
if [ $? -eq 0 ]; then
    echo "  ✅ U8g2 설치 완료"
else
    echo "  ❌ U8g2 설치 실패"
fi

echo "  - DHT sensor library 설치 중..."
arduino-cli lib install "DHT sensor library"
if [ $? -eq 0 ]; then
    echo "  ✅ DHT sensor library 설치 완료"
else
    echo "  ❌ DHT sensor library 설치 실패"
fi
echo ""

# Board B용 라이브러리 설치
echo "[3/4] Board B용 라이브러리 설치 중..."
echo "  - Adafruit NeoPixel 설치 중..."
arduino-cli lib install "Adafruit NeoPixel"
if [ $? -eq 0 ]; then
    echo "  ✅ Adafruit NeoPixel 설치 완료"
else
    echo "  ❌ Adafruit NeoPixel 설치 실패"
fi

echo "  - Stepper 라이브러리 설치 중..."
arduino-cli lib install "Stepper"
if [ $? -eq 0 ]; then
    echo "  ✅ Stepper 라이브러리 설치 완료"
else
    echo "  ❌ Stepper 라이브러리 설치 실패"
fi
echo ""

# 설치 확인
echo "[4/4] 설치된 라이브러리 확인 중..."
echo ""
echo "설치된 라이브러리 목록:"
arduino-cli lib list | grep -E "U8g2|DHT|NeoPixel|Stepper" || echo "라이브러리를 찾을 수 없습니다."
echo ""

echo "=========================================="
echo "✅ 라이브러리 설치 완료!"
echo "=========================================="
echo ""
echo "다음 명령어로 컴파일 테스트를 진행하세요:"
echo "  arduino-cli compile --fqbn arduino:avr:uno ~/smartfarm/board_a"
echo "  arduino-cli compile --fqbn arduino:avr:uno ~/smartfarm/board_b"

