# Arduino CLI 라이브러리 설치 가이드

## 📋 필요한 라이브러리 목록

### Board A (board_a.ino)
- **U8g2** - OLED 디스플레이 제어용
- **DHT sensor library** - DHT11 온습도 센서용

### Board B (board_b.ino)
- **Adafruit NeoPixel** - NeoPixel LED 스트립 제어용
- **Stepper** - 스테퍼 모터 제어용 (Arduino 기본 라이브러리, 별도 설치 불필요)

---

## 🚀 설치 방법

### 1. 라이브러리 검색 및 설치

#### Board A용 라이브러리 설치:

```bash
# U8g2 라이브러리 설치
arduino-cli lib install "U8g2"

# DHT sensor library 설치
arduino-cli lib install "DHT sensor library"
```

#### Board B용 라이브러리 설치:

```bash
# Adafruit NeoPixel 라이브러리 설치
arduino-cli lib install "Adafruit NeoPixel"
```

**참고:** `Stepper.h`는 Arduino 기본 라이브러리이므로 별도 설치가 필요 없습니다.

---

### 2. 한 번에 설치하기 (전체 라이브러리)

```bash
# 모든 필요한 라이브러리를 한 번에 설치
arduino-cli lib install "U8g2" "DHT sensor library" "Adafruit NeoPixel"
```

---

### 3. 설치 확인

설치된 라이브러리 목록 확인:

```bash
arduino-cli lib list
```

특정 라이브러리 검색 (이름이 정확하지 않을 경우):

```bash
# U8g2 검색
arduino-cli lib search U8g2

# DHT 검색
arduino-cli lib search DHT

# NeoPixel 검색
arduino-cli lib search NeoPixel
```

---

### 4. 라이브러리 버전 확인

```bash
# 설치된 라이브러리 상세 정보
arduino-cli lib list | grep -E "U8g2|DHT|NeoPixel"
```

---

## 📝 상세 라이브러리 정보

### U8g2
- **라이브러리 이름:** `U8g2`
- **용도:** SH1106 OLED 디스플레이 (128x64) 제어
- **공식 저장소:** https://github.com/olikraus/u8g2

### DHT sensor library
- **라이브러리 이름:** `DHT sensor library`
- **용도:** DHT11/DHT22 온습도 센서 읽기
- **공식 저장소:** https://github.com/adafruit/DHT-sensor-library

### Adafruit NeoPixel
- **라이브러리 이름:** `Adafruit NeoPixel`
- **용도:** NeoPixel RGBW LED 스트립 제어
- **공식 저장소:** https://github.com/adafruit/Adafruit_NeoPixel

---

## ⚠️ 주의사항

1. **라이브러리 이름 정확성**
   - arduino-cli는 라이브러리 이름을 정확히 입력해야 합니다
   - 이름이 확실하지 않으면 `arduino-cli lib search <키워드>`로 먼저 검색하세요

2. **대소문자 구분**
   - 라이브러리 이름은 대소문자를 구분합니다
   - 예: `U8g2` (대문자 U, 소문자 8g2)

3. **권한 문제**
   - 설치 시 권한 오류가 발생하면 `sudo`를 사용하지 마세요
   - arduino-cli는 사용자 디렉토리에 라이브러리를 설치합니다

---

## 🔧 문제 해결

### 라이브러리를 찾을 수 없는 경우:

```bash
# 라이브러리 인덱스 업데이트
arduino-cli lib update-index

# 다시 검색
arduino-cli lib search <라이브러리명>
```

### 설치 후에도 컴파일 오류가 발생하는 경우:

1. 라이브러리가 제대로 설치되었는지 확인:
   ```bash
   arduino-cli lib list
   ```

2. 라이브러리 경로 확인:
   ```bash
   arduino-cli config dump | grep user
   ```

3. 라이브러리 재설치:
   ```bash
   arduino-cli lib uninstall <라이브러리명>
   arduino-cli lib install <라이브러리명>
   ```

---

## ✅ 설치 완료 후 테스트

라이브러리 설치가 완료되면 컴파일 테스트를 진행하세요:

```bash
# Board A 컴파일 테스트
arduino-cli compile --fqbn arduino:avr:uno ~/smartfarm/board_a

# Board B 컴파일 테스트
arduino-cli compile --fqbn arduino:avr:uno ~/smartfarm/board_b
```

컴파일이 성공하면 모든 라이브러리가 제대로 설치된 것입니다! 🎉

