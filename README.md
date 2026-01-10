# 🌿 베란다 스마트팜 (Veranda SmartFarm)

라즈베리파이와 아두이노를 이용한 지능형 가정용 자동화 스마트팜 시스템입니다.  
딸기와 상추 재배를 위한 최적 환경을 자동으로 유지합니다.

---

## 🚀 주요 기능

### 📊 실시간 모니터링
- **센서 데이터**: 온도, 습도, 토양습도, 조도 (Lux)
- **계산값**: VPD(수증기압차), DLI(일조량), PPFD(광합성 광량)
- **구동계 상태**: LED, 팬, 밸브, 커튼, 비상정지 상태 실시간 표시

### 🤖 지능형 자동화 제어
- **물주기**: 토양습도 + VPD 기반 통합 제어 (점적스파이크 8개)
- **LED 조명**: 시간대별 DLI 예측 기반 자동 제어 (화이트/보라색 LED)
- **환기 팬**: VPD + 온습도 기반 자동 제어
- **커튼**: VPD 기반 자동 개폐 (스테퍼 모터)
- **카메라**: 주기적 자동 촬영 (월별 폴더 관리)

### 🌐 웹 대시보드
- **원격 접속**: 외부 네트워크에서 접속 가능 (포트포워딩 지원)
- **실시간 모니터링**: 센서값, 구동계 상태 실시간 표시
- **데이터 시각화**: 
  - 동적 그래프 (Chart.js)
  - 날짜 범위 선택
  - 시간 범위 조정 (슬라이더)
  - Y축 스케일 조정 (슬라이더)
  - 데이터 계열 선택 (체크박스)
- **상태 분석**: 
  - 이상 상황 자동 감지 및 경고
  - 권장 조치사항 제시
  - 정상 상태 표시
  - 경고 케이스 도움말

### 📝 로그 시스템
- **CSV 기반 저장**: 일일 로그 파일 자동 생성
- **월별 폴더 관리**: `logs/YYYY-MM/` 구조
- **자동 용량 관리**: 디스크 용량 초과 시 오래된 파일 자동 삭제
- **데이터 필드**: 센서값, 구동계 상태/값, 계산값, 일일 통계 등 19개 필드

### 🔔 알림 시스템
- **상태 분석**: 실시간 데이터 기반 이상 감지
- **경고 분류**: ERROR(즉각 조치), WARNING(주의), INFO(정보)
- **케이스 코드**: Discord 푸시 알림 준비 (각 경고에 고유 코드 부여)
- **도움말**: 모든 경고 케이스 목록 및 설명 제공

---

## 🛠️ 빠른 시작

### 1. 시스템 서비스 제어

```bash
# 메인 서비스 (센서/자동화)
svc-on        # 서비스 시작
svc-off       # 서비스 중지
svc-restart   # 서비스 재시작
svc-status    # 상태 확인
svc-log       # 실시간 로그 확인

# 웹 서버
web-on        # 웹 서버 시작
web-off       # 웹 서버 중지
web-restart   # 웹 서버 재시작
web-status    # 상태 확인
web-log       # 실시간 로그 확인
```

> 💡 **팁**: `farm-help` 명령어로 모든 단축키 확인 가능

### 2. 웹 대시보드 접속

#### 로컬 네트워크
```
http://[라즈베리파이_IP]:5000
```

#### 외부 네트워크 (포트포워딩 설정 후)
```
http://[공인_IP]:5000
```

**기본 로그인 정보**:
- 사용자명: `admin`
- 비밀번호: `smartfarm2026` (변경 권장, `config.py`에서 수정)

> 📖 자세한 설정: `guides/WEB_DASHBOARD_SETUP.md`, `guides/MOBILE_ACCESS.md`

### 3. 설정 변경

주요 설정은 `config.py` 파일에서 관리합니다:
- 자동화 스위치 (물주기, LED, 팬, 커튼)
- 센서 임계값
- LED 제어 시간대
- 물주기 설정
- 디스크 용량 관리

> ⚠️ **보안**: `config.py`는 Git에서 제외됩니다 (`.gitignore`)

---

## 📁 프로젝트 구조

```
smartfarm/
├── main.py              # 메인 구동 코드
├── automation.py         # 자동화 로직 (VPD/DLI 기반)
├── logger.py            # 로깅 시스템 (CSV, 월별 폴더, 자동 용량 관리)
├── web_server.py        # 웹 대시보드 서버 (Flask)
├── data_reader.py       # 데이터 읽기 모듈 (CSV/MariaDB 추상화)
├── analyzer.py          # 상태 분석 및 알림 생성
├── camera.py            # 카메라 제어
├── utils.py             # 유틸리티 함수
├── config.py            # 설정 파일 (Git 제외)
│
├── board_a/             # 아두이노 센서 보드 (Arduino Uno)
│   └── board_a.ino      # 센서 읽기, OLED 표시
├── board_b/             # 아두이노 구동계 보드 (Arduino Uno)
│   └── board_b.ino      # 릴레이, 모터 제어
│
├── templates/           # 웹 대시보드 HTML 템플릿
│   ├── index.html       # 메인 대시보드
│   └── login.html       # 로그인 페이지
├── static/              # 웹 대시보드 정적 파일
│   ├── css/style.css    # 스타일시트
│   └── js/dashboard.js  # 클라이언트 로직
│
├── logs_data/           # 센서 데이터 로그 (CSV, Git 제외)
│   └── YYYY-MM/         # 월별 폴더
│       └── smartfarm_log_YYYY-MM-DD.csv
├── logs_system/         # 시스템 로그 (smartfarm.log, Git 제외)
│   ├── old/             # 기존 smartfarm.log 보관
│   └── YYYY-MM/         # 월별 폴더
│       └── smartfarm_YYYY-MM-DD.log
├── images/              # 카메라 이미지 (Git 제외)
│   └── YYYY-MM/         # 월별 폴더
│       ├── auto/        # 자동 촬영
│       └── manual/      # 수동 촬영
│
├── guides/              # 설정 가이드 문서
│   ├── WEB_DASHBOARD_SETUP.md    # 웹 대시보드 설정
│   ├── MOBILE_ACCESS.md          # 모바일 접속 가이드
│   ├── ARDUINO_SETUP.md          # 아두이노 설정
│   ├── LED_CONTROL_LOGIC.md      # LED 제어 로직 상세
│   └── DEV_LOG.md                # 개발 로그
│
├── cursor_log/          # 개발 기록 문서 (Git 포함)
│   └── YYYYMMDD-HHMMSS-*.md
│
├── my_aliases           # Bash 단축키 설정
└── README.md            # 이 파일
```

---

## 🧠 자동화 알고리즘

### 물주기 제어
- **우선순위 1**: 토양습도 < 30% → 급수 시작
- **우선순위 2**: VPD > 1.5 + 토양습도 < 50% → 보조 급수
- **안전 체크**: 토양습도 ≥ 50% 또는 VPD < 0.8 → 급수 중단
- **야간 모드**: 22시 ~ 6시 급수 금지
- **쿨타임**: 급수 후 1시간 대기

### LED 조명 제어
- **작동 시간**: 6시 ~ 20시 (광합성 활성 시간대)
- **조건 1**: 자연광 < 500 Lux → 즉시 LED 켜기
- **조건 2**: 현재 DLI < 시간대별 목표의 70% → LED 켜기
- **조건 3**: 예상 총 DLI < 목표의 80% → LED 켜기
- **화이트 LED**: 주 조명 (100% 밝기)
- **보라색 LED**: DLI < 목표의 70%일 때 보조 조명
- **페이드**: 10분 동안 서서히 밝아지기/꺼지기 (광충격 방지)

> 📖 상세 로직: `guides/LED_CONTROL_LOGIC.md`

### 환기 팬 제어
- **VPD 기반**: VPD > 1.8 → 팬 ON, VPD < 1.2 → 팬 OFF
- **온도 기반**: 온도 > 32°C → 팬 ON
- **습도 기반**: 습도 > 80% → 팬 ON

### 커튼 제어
- **VPD 낮음** (습도 높음): VPD < 0.6 → 커튼 열기
- **VPD 높음** (건조): VPD > 1.5 → 커튼 닫기
- **스테퍼 모터**: 초기 상태, 방향, 회전수 설정 가능

---

## 📊 데이터 로깅

### 로그 구조
- **기록 간격**: 10초마다
- **파일 형식**: CSV
- **필드 수**: 19개
  - 센서값: 온도, 습도, 토양습도, 조도
  - 계산값: VPD, DLI
  - 구동계 상태: 밸브, 팬, LED(화이트/보라색), 커튼, 비상정지
  - 구동계 값: 팬 속도(%), LED 밝기(%)
  - 일일 통계: 물주기 횟수, 물 사용량(L)

### 용량 관리
- **자동 삭제**: logs + images 합산 10GB 초과 시 오래된 파일부터 삭제
- **안전 여유공간**: 최소 2GB 유지
- **정리 주기**: 1시간마다 자동 체크

---

## 🔐 보안

### 인증
- **웹 대시보드**: 세션 기반 인증
- **비밀번호 설정**: `config.py`의 `WEB_PASSWORD` (Git 제외)
- **HTTPS 권장**: 프로덕션 환경에서는 nginx + Let's Encrypt 사용 권장

### 파일 보안
- `config.py`: Git 제외 (비밀번호 포함)
- `logs_data/`, `logs_system/`, `images/`: Git 제외 (용량 및 개인정보)

---

## 🛠️ 개발 및 유지보수

### 아두이노 펌웨어 업데이트
```bash
farm-up-a    # Board A (센서/OLED) 업데이트
farm-up-b    # Board B (구동계) 업데이트
```

### 로그 확인
```bash
svc-log      # 메인 서비스 로그
web-log      # 웹 서버 로그
tail -f logs_system/$(date +%Y-%m)/smartfarm_$(date +%Y-%m-%d).log  # 파일 로그
```

### 서비스 관리
- **메인 서비스**: `/etc/systemd/system/smartfarm.service`
- **웹 서버**: `/etc/systemd/system/smartfarm-web.service`
- **자동 시작**: 재부팅 시 자동 실행 (enabled)

---

## 📚 가이드 문서

모든 설정 가이드는 `guides/` 폴더에 있습니다:

- **`WEB_DASHBOARD_SETUP.md`**: 웹 대시보드 설치 및 설정
- **`MOBILE_ACCESS.md`**: 모바일 접속 방법
- **`ARDUINO_SETUP.md`**: 아두이노 보드 설정
- **`LED_CONTROL_LOGIC.md`**: LED 제어 로직 상세 분석
- **`DEV_LOG.md`**: 개발 로그

개발 기록은 `cursor_log/` 폴더에 있습니다.

---

## 🔄 향후 계획

- [ ] MariaDB 연동 (CSV → 데이터베이스)
- [ ] Discord 푸시 알림 구현
- [ ] 계절별 LED 작동 시간 자동 조정
- [ ] 날씨 API 연동 (일조량 예측)
- [ ] 로그 분석 리포트 자동 생성

---

## 📝 라이선스

이 프로젝트는 개인 사용 목적으로 개발되었습니다.

---

## 👤 작성자

베란다 스마트팜 프로젝트  
개발 도구: Cursor AI

---

**최종 업데이트**: 2026-01-03
