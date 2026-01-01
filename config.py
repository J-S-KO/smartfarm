import os

# ==========================================
# 🔌 포트 및 통신 설정
# ==========================================
PORT_A = '/dev/ttyBoardA'  # 센서 보드
PORT_B = '/dev/ttyBoardB'  # 액추에이터 보드
BAUD_RATE = 9600

# ==========================================
# 📁 파일 저장 경로
# ==========================================
BASE_DIR = '/home/pi/smartfarm'
LOG_DIR = os.path.join(BASE_DIR, 'logs')
IMG_DIR = os.path.join(BASE_DIR, 'images')

# ==========================================
# 💾 용량 관리 설정
# ==========================================
# SD카드 용량: 16GB (실질 14.8GB)
# 최소 여유공간: 2GB 유지
# logs + images 합산 용량 제한: 10GB (초과 시 오래된 파일부터 삭제)
DISK_TOTAL_GB = 14.8          # 전체 용량 (GB)
DISK_MIN_FREE_GB = 2.0        # 최소 여유공간 (GB)
STORAGE_LIMIT_GB = 10.0       # logs + images 합산 제한 (GB)

# ==========================================
# 🛡️ 자동화 마스터 스위치 (Safety Flags)
# ==========================================
USE_AUTO_WATER = False   # [중요] 테스트 완료 전까지 False 유지
USE_AUTO_LED   = False
USE_AUTO_FAN   = False
USE_AUTO_CURTAIN = False  # 커튼 제어 (스테퍼 모터)
USE_AUTO_CAM   = True

# ==========================================
# 🧠 자동화 상세 설정 (Brain Config)
# ==========================================

# 1. 💧 물주기 설정
# 점적스파이크: 2L/h 스펙, 상추 화분(5개), 딸기 화분(3개)
DRIP_FLOW_RATE_LH = 2.0   # 점적스파이크 유량 (L/h)
LETTUCE_DRIPS = 5         # 상추 화분 점적스파이크 개수
STRAWBERRY_DRIPS = 3      # 딸기 화분 점적스파이크 개수
# 화분 크기: 660*200*200mm (약 26.4L)
POT_VOLUME_L = 26.4       # 화분 용량 (L)

# 토양습도 기반 물주기 (딸기 화분 센서 기준)
SOIL_TRIGGER_PCT = 30     # 30% 미만이면 급수 시작
SOIL_SAFE_PCT = 50        # 50% 이상이면 안전 (물주기 중단)
WATERING_DURATION = 5     # 1회 급수 시간 (초) - 짧게 설정하여 홍수 방지
WATER_COOLDOWN = 3600     # 급수 후 휴식 시간 (초, 1시간)

# VPD 기반 물주기 (우선순위: 토양습도 > VPD)
VPD_HIGH_TRIGGER = 1.5    # VPD 1.5 이상이면 공기 건조 -> 물주기 고려
VPD_LOW_SAFE = 0.8        # VPD 0.8 이하면 안전 (물주기 중단)

# 2. 🌙 야간 모드 (물주기 금지 시간)
NIGHT_START_HOUR = 22     # 밤 10시부터
NIGHT_END_HOUR = 6        # 아침 6시까지 (이 사이에는 물 안 줌)

# 3. ☀️ 조명 설정 (일조량 기반)
LED_ON_HOUR = 8           # 08:00 ON
LED_OFF_HOUR = 20         # 20:00 OFF

# 일조량 목표 (DLI: Daily Light Integral, mol/m²/day)
# 딸기: 12-17 mol/m²/day, 상추: 12-16 mol/m²/day
TARGET_DLI_MIN = 12.0     # 최소 일조량 목표 (mol/m²/day)
TARGET_DLI_MAX = 17.0     # 최대 일조량 목표 (mol/m²/day)

# 조도 센서 기준 (Lux -> PPFD 변환 계수: 0.0185)
LUX_TO_PPFD = 0.0185      # Lux를 PPFD(μmol/m²/s)로 변환
MIN_LUX_THRESHOLD = 500   # 자연광이 이 값 미만이면 LED 보조 필요

# LED 제어 (화이트 LED + 보라색 LED)
LED_WHITE_PRIORITY = True # 화이트 LED 우선 사용 (일반 조명)
LED_PURPLE_BOOST = True   # 보라색 LED 보조 사용 (식물 생장)

# LED 페이드 인/아웃 설정 (식물 광충격 방지)
LED_FADE_DURATION_SEC = 600  # 페이드 시간 (초, 10분 = 600초)
LED_FADE_STEP_MS = 100       # 페이드 업데이트 간격 (밀리초, 0.1초마다 업데이트)

# 4. 🌬️ 환기 설정 (VPD 기반)
TEMP_HIGH_LIMIT = 32      # 32도 이상 팬 ON
HUM_HIGH_LIMIT = 80       # 80% 이상 팬 ON

# VPD 기반 환기 (VPD가 너무 높으면 공기 건조 -> 팬 조절)
VPD_FAN_ON = 1.8          # VPD 1.8 이상이면 팬 ON (공기 순환)
VPD_FAN_OFF = 1.2         # VPD 1.2 이하면 팬 OFF

# 5. 🪟 커튼 제어 (VPD 기반)
# VPD가 낮으면 (습도 높음) 커튼 열기, VPD가 높으면 (건조) 커튼 닫기
VPD_CURTAIN_OPEN = 0.6    # VPD 0.6 이하면 커튼 열기 (습도 높음)
VPD_CURTAIN_CLOSE = 1.5   # VPD 1.5 이상이면 커튼 닫기 (건조)

# 스테퍼 모터 커튼 설정
CURTAIN_INITIAL_STATE = "CLOSED"  # 초기 상태: "CLOSED" 또는 "OPEN"
CURTAIN_OPEN_DIRECTION = "CCW"    # 열기 방향: "CCW" (반시계) 또는 "CW" (시계)
CURTAIN_STEPS_PER_REVOLUTION = 2048  # 스테퍼 모터 1바퀴 스텝 수
CURTAIN_REVOLUTIONS = 1.0         # 완전 Open/Close에 필요한 회전 수 (바퀴)
CURTAIN_STEPS_OPEN = int(CURTAIN_STEPS_PER_REVOLUTION * CURTAIN_REVOLUTIONS)  # 열기 스텝 수
CURTAIN_STEPS_CLOSE = int(CURTAIN_STEPS_PER_REVOLUTION * CURTAIN_REVOLUTIONS)  # 닫기 스텝 수

# 6. 📷 카메라 설정
CAM_INTERVAL_MIN = 30     # 30분 간격

