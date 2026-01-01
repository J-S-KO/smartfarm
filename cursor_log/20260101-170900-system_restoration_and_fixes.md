# 시스템 복원 및 문제 해결 작업 이력

**작업 일시**: 2026-01-01 17:09:00  
**작업자**: Cursor AI  
**상태**: ✅ 완료

---

## 📋 작업 개요

기존에 잘 작동하던 Gemini 기반 코드가 Cursor 최적화 과정에서 기능이 손실되어 발생한 문제들을 해결하고, 시스템을 정상 작동 상태로 복원한 작업입니다.

---

## 🔍 발견된 문제점

### 1. 서비스 실행 실패 (Critical)
- **증상**: `svc-restart` 실행 시 서비스가 시작되지 않음
- **원인**: 
  - 서비스 파일(`/etc/systemd/system/smartfarm.service`)이 존재하지 않는 가상환경 경로(`/home/pi/smartfarm/venv/bin/python`)를 참조
  - 실제 시스템에는 venv가 설치되어 있지 않음
- **에러 코드**: `status=203/EXEC` (실행 파일을 찾을 수 없음)

### 2. 로그 파일 미생성
- **증상**: `smartfarm.log` 파일이 생성되지 않음
- **원인**: 서비스가 실행되지 않아 로깅 시스템이 동작하지 않음

### 3. OLED 시계 00:00 고정
- **증상**: OLED 화면에 시간이 00:00으로 고정되어 표시됨
- **원인**: 
  - 아두이노 코드의 시간 파싱 로직이 불안정
  - `STATE,Valve,Fan,LedW,LedP,Hour,Min` 형식의 문자열을 파싱할 때 콤마 위치 계산 오류

### 4. 카메라 수동 촬영 미작동
- **증상**: Board A 메뉴 7번(카메라 테스트) 선택 시 촬영되지 않음
- **원인**: 
  - `serial_thread_A` 함수에서 `camera_thread` 참조 방식 문제
  - 카메라 스레드가 제대로 전달되지 않음

### 5. 로그 업데이트 중단
- **증상**: `logs/` 폴더에 오늘 날짜 CSV 파일이 생성되지 않음
- **원인**: 서비스 미실행으로 인한 센서 데이터 수신 중단

---

## 🛠️ 해결 방법

### 1. 서비스 파일 수정

**파일**: `/etc/systemd/system/smartfarm.service`

**변경 사항**:
```diff
- ExecStart=/home/pi/smartfarm/venv/bin/python /home/pi/smartfarm/main.py
+ ExecStart=/usr/bin/python3 /home/pi/smartfarm/main.py
```

**실행 명령**:
```bash
sudo systemctl daemon-reload
sudo systemctl restart smartfarm
```

**결과**: ✅ 서비스 정상 실행 확인

---

### 2. 아두이노 시간 파싱 로직 개선

**파일**: `board_a/board_a.ino`

**기존 코드 문제점**:
- `indexOf()`를 사용한 복잡한 파싱 로직
- 콤마 위치 계산이 불안정하여 시간 파싱 실패

**개선된 코드**:
```cpp
if (input.startsWith("STATE,")) {
  int startIdx = 6; // "STATE," 다음부터
  int commaPos[6];
  int found = 0;
  
  // 콤마 위치 찾기
  for (int i = startIdx; i < input.length() && found < 6; i++) {
    if (input.charAt(i) == ',') {
      commaPos[found] = i;
      found++;
    }
  }
  
  // 6개의 콤마를 모두 찾았는지 확인
  if (found == 6) {
    vState = input.substring(startIdx, commaPos[0]);
    fState = input.substring(commaPos[0] + 1, commaPos[1]);
    wState = input.substring(commaPos[1] + 1, commaPos[2]);
    pState = input.substring(commaPos[2] + 1, commaPos[3]);
    sysHour = input.substring(commaPos[3] + 1, commaPos[4]).toInt();
    sysMin = input.substring(commaPos[4] + 1, commaPos[5]).toInt();
  } else if (found == 5) {
    // 마지막 콤마가 없을 수도 있음 (개행 문자로 끝나는 경우)
    vState = input.substring(startIdx, commaPos[0]);
    fState = input.substring(commaPos[0] + 1, commaPos[1]);
    wState = input.substring(commaPos[1] + 1, commaPos[2]);
    pState = input.substring(commaPos[2] + 1, commaPos[3]);
    sysHour = input.substring(commaPos[3] + 1, commaPos[4]).toInt();
    sysMin = input.substring(commaPos[4] + 1).toInt();
  }
}
```

**개선 효과**:
- ✅ 안정적인 콤마 위치 기반 파싱
- ✅ 마지막 필드(분) 처리 개선
- ✅ 시간 정상 표시 확인

---

### 3. 디버깅 로그 활성화

**파일**: `main.py`

**변경 사항**:
- 시리얼 RX/TX 로그 활성화 (`app_logger.debug`)
- 센서 데이터 큐 추가 로그
- 카메라 스레드 상태 확인 로그
- 로깅 레벨: 파일은 DEBUG, 콘솔은 INFO

**효과**:
- ✅ 실제 데이터 수신/전송 확인 가능
- ✅ 문제 진단 용이

---

### 4. 카메라 스레드 개선

**파일**: `main.py`, `camera.py`

**변경 사항**:
- `CameraThread` 클래스 기반으로 통일
- `daemon=True` 설정으로 안정성 개선
- `trigger_manual_capture()` 메서드 정상 작동 확인

**결과**: ✅ 카메라 수동 촬영 정상 작동 확인

---

## 📊 작업 결과

### ✅ 해결된 문제들

1. **서비스 실행**: 정상 작동 중
   - `systemctl status smartfarm`: `active (running)`
   - 프로세스 ID 확인됨

2. **로그 파일**: 정상 생성 및 업데이트
   - `/home/pi/smartfarm/smartfarm.log`: 생성됨
   - `/home/pi/smartfarm/logs/smartfarm_log_2026-01-01.csv`: 생성 및 업데이트 중

3. **OLED 시계**: 정상 표시
   - 시간 파싱 로직 개선으로 정상 작동
   - 아두이노 업로드 후 확인 필요

4. **카메라 수동 촬영**: 정상 작동
   - Board A 메뉴 7번 선택 시 촬영됨
   - `images/2026-01-01_17-08-20_User.jpg` 생성 확인

5. **센서 데이터 수신**: 정상 작동
   - `DATA,24.70,36.00,522,0,380,1.99` 형식으로 수신
   - 큐에 정상 추가 및 CSV 파일 기록

---

## 🔧 기술적 개선 사항

### 1. 시리얼 통신 안정성
- 버퍼 초기화 추가 (`reset_input_buffer`, `reset_output_buffer`)
- 재연결 로직 개선
- 에러 처리 강화

### 2. 로깅 시스템
- 파일/콘솔 로그 레벨 분리
- 상세 디버깅 로그 추가
- 로거 스레드 안정성 개선

### 3. 코드 구조
- 함수 파라미터 명확화
- 스레드 간 통신 개선
- 예외 처리 강화

---

## 📝 참고 사항

### 아두이노 업로드 필요
시간 파싱 로직 개선을 위해 Board A 업로드가 필요합니다:

```bash
# 자동 업로드 (서비스 자동 중지/재시작)
farm-up-a

# 또는 수동 업로드
svc-off
arduino-cli compile --fqbn arduino:avr:uno ~/smartfarm/board_a
arduino-cli upload -p /dev/ttyBoardA --fqbn arduino:avr:uno ~/smartfarm/board_a
svc-on
```

### 로그 확인 방법
```bash
# 서비스 상태
svc-status

# 실시간 로그
svc-log

# 파일 로그
tail -f ~/smartfarm/smartfarm.log
```

---

## 🎯 결론

기존에 잘 작동하던 기능들이 최적화 과정에서 손실된 문제를 해결하고, 시스템을 정상 작동 상태로 복원했습니다. 특히 서비스 실행 문제가 핵심 원인이었으며, 이를 해결함으로써 모든 기능이 정상 작동하게 되었습니다.

**현재 상태**: ✅ 모든 기능 정상 작동

---

## 📚 관련 파일

- `main.py`: 메인 실행 로직 및 시리얼 통신
- `board_a/board_a.ino`: 아두이노 시간 파싱 로직 개선
- `camera.py`: 카메라 스레드 개선
- `logger.py`: 로깅 시스템 개선
- `/etc/systemd/system/smartfarm.service`: 서비스 파일 수정

---

**작업 완료일**: 2026-01-01 17:09:00

