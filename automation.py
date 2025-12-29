import time
from datetime import datetime
import config

# 상태 기록 (Global State)
last_watering_time = 0

def automation_loop(stop_event, sys_state, ser_b, ser_b_lock):
    global last_watering_time
    print("[Auto] 스마트팜 두뇌 가동 (야간 모드 & 쿨타임 적용)")

    while not stop_event.is_set():
        # 1. 현재 시간 및 센서값 읽기
        now = datetime.now()
        current_hour = now.hour
        
        # sys_state에서 값 가져오기 (없으면 안전한 기본값)
        curr_soil = sys_state.get('soil_pct', 100) # 기본값 100(습함)으로 두어 오작동 방지
        curr_temp = sys_state.get('temp', 0)
        curr_hum  = sys_state.get('hum', 0)
        
        # -------------------------------------------------------
        # 🌙 야간 모드 판별
        # -------------------------------------------------------
        # 밤 10시(22) ~ 아침 6시(6) 사이인지 확인
        is_night = False
        if config.NIGHT_START_HOUR <= current_hour or current_hour < config.NIGHT_END_HOUR:
            is_night = True
            
        # -------------------------------------------------------
        # 💧 자동 급수 로직 (Safety First)
        # -------------------------------------------------------
        if config.USE_AUTO_WATER:
            # 물을 주면 안 되는 상황 체크
            if is_night:
                # (옵션) 밤에는 로그를 너무 자주 찍지 않도록 처리 가능
                pass 
            else:
                # 낮이고, 흙이 마랐고, 쿨타임이 지났다면?
                time_since_last = time.time() - last_watering_time
                
                if (curr_soil < config.SOIL_TRIGGER_PCT) and \
                   (time_since_last > config.WATER_COOLDOWN):
                    
                    print(f"⚠️ [Auto] 토양 건조 ({curr_soil}%) -> 급수 시작")
                    
                    # [안전한 급수 시퀀스]
                    # 1. 밸브 ON
                    send_cmd(ser_b, ser_b_lock, "M1") 
                    
                    # 2. 설정된 시간만큼 대기 (물 주는 중)
                    time.sleep(config.WATERING_DURATION)
                    
                    # 3. 밸브 OFF (반드시 꺼야 함!)
                    send_cmd(ser_b, ser_b_lock, "M1")
                    
                    # 4. 기록 업데이트
                    last_watering_time = time.time()
                    print(f"✅ [Auto] 급수 완료 (다음 급수까지 {config.WATER_COOLDOWN}초 대기)")

        # -------------------------------------------------------
        # ☀️ 조명 제어 로직 (시간 기반)
        # -------------------------------------------------------
        # 현재 아두이노가 Toggle(M0) 방식이라 상태 확인 없이 보내면 꼬일 수 있음.
        # 추후 아두이노 코드 수정 후 적용 권장.
        # if config.USE_AUTO_LED:
        #     if config.LED_ON_HOUR <= current_hour < config.LED_OFF_HOUR:
        #         # 낮 시간 -> 켜기
        #         pass
        #     else:
        #         # 밤 시간 -> 끄기
        #         pass

        # -------------------------------------------------------
        # 🌬️ 환기 팬 제어
        # -------------------------------------------------------
        if config.USE_AUTO_FAN:
            if curr_temp > config.TEMP_HIGH_LIMIT:
                # 고온 경보 -> 팬 작동 로직
                pass

        time.sleep(1) # CPU 과부하 방지 (1초 휴식)

def send_cmd(ser, lock, cmd):
    """아두이노로 명령 전송 (스레드 안전)"""
    if ser and ser.is_open:
        with lock:
            try:
                ser.write((cmd + '\n').encode())
                print(f"[Auto] 명령 전송: {cmd}")
                time.sleep(0.1) # 전송 안정성 확보
            except Exception as e:
                print(f"[Auto] 전송 실패: {e}")