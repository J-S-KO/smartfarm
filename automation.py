import time
from datetime import datetime
import serial
import config
from logger import app_logger

# 상태 기록 (Global State)
last_watering_time = 0
last_dli_reset_time = 0
accumulated_dli = 0.0
watering_count_today = 0  # 오늘 물주기 횟수
total_water_used_today = 0.0  # 오늘 사용한 물 총량 (L)
curtain_state = None  # 커튼 상태: "OPEN" 또는 "CLOSED" (초기값 None = 초기화 필요)

def calculate_vpd(temp, hum):
    """
    VPD (Vapor Pressure Deficit) 계산
    Args:
        temp: 온도 (°C)
        hum: 습도 (%)
    Returns:
        VPD 값 (kPa)
    """
    if temp <= 0 or hum < 0 or hum > 100:
        return 0.0
    
    # 포화 수증기압 계산 (Tetens 공식)
    es = 0.61078 * (2.71828 ** ((17.27 * temp) / (temp + 237.3)))
    # 실제 수증기압 계산
    ea = es * (hum / 100.0)
    # VPD 계산
    vpd = es - ea
    return vpd

def calculate_ppfd_from_lux(lux):
    """
    Lux를 PPFD (μmol/m²/s)로 변환
    """
    return lux * config.LUX_TO_PPFD

def update_dli(ppfd, dt_seconds):
    """
    DLI (Daily Light Integral) 누적 업데이트
    Args:
        ppfd: PPFD 값 (μmol/m²/s)
        dt_seconds: 경과 시간 (초)
    Returns:
        누적 DLI 값 (mol/m²/day)
    """
    global accumulated_dli, last_dli_reset_time
    
    # 자정에 DLI 리셋
    now = time.time()
    if last_dli_reset_time == 0:
        last_dli_reset_time = now
    
    # 자정 체크 (간단하게 24시간 경과 시 리셋)
    if now - last_dli_reset_time > 86400:  # 24시간
        accumulated_dli = 0.0
        last_dli_reset_time = now
        app_logger.info("[Auto] DLI 리셋 (새로운 하루 시작)")
    
    # DLI 누적 (PPFD * 시간(초) / 1,000,000)
    dli_increment = (ppfd * dt_seconds) / 1000000.0
    accumulated_dli += dli_increment
    
    return accumulated_dli

def automation_loop(stop_event, sys_state, ser_b, ser_b_lock, state_lock):
    global last_watering_time, accumulated_dli, last_dli_reset_time
    global watering_count_today, total_water_used_today, curtain_state
    
    app_logger.info("[Auto] 스마트팜 자동화 시스템 가동 (VPD, 일조량, 토양습도 통합 제어)")
    
    # 커튼 초기 상태 설정
    if curtain_state is None:
        curtain_state = config.CURTAIN_INITIAL_STATE
        app_logger.info(f"[Auto] 🪟 커튼 초기 상태: {curtain_state}")
    
    last_loop_time = time.time()
    last_day_reset = datetime.now().day
    
    while not stop_event.is_set():
        loop_start = time.time()
        dt = loop_start - last_loop_time
        last_loop_time = loop_start
        
        # 1. 현재 시간 및 센서값 읽기
        now = datetime.now()
        current_hour = now.hour
        current_day = now.day
        
        # 자정에 일일 통계 리셋
        if current_day != last_day_reset:
            watering_count_today = 0
            total_water_used_today = 0.0
            last_day_reset = current_day
            # sys_state에도 리셋 반영
            with state_lock:
                sys_state['watering_count_today'] = 0
                sys_state['water_used_today'] = 0.0
            app_logger.info("[Auto] 📊 일일 통계 리셋 (새로운 하루 시작)")
        
        # sys_state에서 값 가져오기 (없으면 안전한 기본값)
        with state_lock:
            curr_soil = sys_state.get('soil_pct', 100)  # 기본값 100(습함)으로 두어 오작동 방지
            curr_temp = sys_state.get('temp', 0)
            curr_hum = sys_state.get('hum', 0)
            curr_lux = sys_state.get('lux', 0)
            curr_vpd = sys_state.get('vpd', 0.0)
            current_valve = sys_state.get('valve_status', 'OFF')
            current_fan = sys_state.get('fan_status', 'OFF')
            current_led_w = sys_state.get('led_w_status', 'OFF')
            current_led_p = sys_state.get('led_p_status', 'OFF')
            emergency_stop = sys_state.get('emergency_stop', False)  # 비상 정지 상태
        
        # VPD 재계산 (센서값이 유효한 경우)
        if curr_temp > 0 and 0 < curr_hum <= 100:
            calculated_vpd = calculate_vpd(curr_temp, curr_hum)
            if calculated_vpd > 0:
                curr_vpd = calculated_vpd
                with state_lock:
                    sys_state['vpd'] = calculated_vpd
        
        # DLI 업데이트
        if curr_lux > 0:
            ppfd = calculate_ppfd_from_lux(curr_lux)
            dli = update_dli(ppfd, dt)
            with state_lock:
                sys_state['dli'] = dli
        
        # -------------------------------------------------------
        # 🌙 야간 모드 판별
        # -------------------------------------------------------
        is_night = False
        if config.NIGHT_START_HOUR <= current_hour or current_hour < config.NIGHT_END_HOUR:
            is_night = True
        
        # -------------------------------------------------------
        # 🛑 비상 정지 상태 체크 (최우선 안전 장치)
        # 비상 정지 중에는 모든 자동화 동작 중단
        # (물주기, LED, 팬, 커튼 모두 작동 안 함)
        # 단, 센서 데이터 수집과 DLI 계산은 계속됨
        # -------------------------------------------------------
        
        # -------------------------------------------------------
        # 💧 자동 급수 로직 (토양습도 우선, VPD 보조)
        # -------------------------------------------------------
        if config.USE_AUTO_WATER and not emergency_stop:
            should_water = False
            water_reason = ""
            
            # 우선순위 1: 토양습도 체크 (딸기 화분 센서 기준)
            if curr_soil < config.SOIL_TRIGGER_PCT:
                should_water = True
                water_reason = f"토양 건조 ({curr_soil}% < {config.SOIL_TRIGGER_PCT}%)"
            # 우선순위 2: VPD 체크 (공기 건조 시 보조 급수)
            elif curr_vpd > config.VPD_HIGH_TRIGGER and curr_soil < config.SOIL_SAFE_PCT:
                should_water = True
                water_reason = f"VPD 높음 ({curr_vpd:.2f} > {config.VPD_HIGH_TRIGGER}) + 토양 보통"
            
            # 물을 주면 안 되는 상황 체크
            if should_water:
                # 안전 체크: 토양이 이미 충분히 습하면 물주기 중단
                if curr_soil >= config.SOIL_SAFE_PCT:
                    should_water = False
                    water_reason = f"토양 충분히 습함 ({curr_soil}% >= {config.SOIL_SAFE_PCT}%)"
                # VPD가 너무 낮으면 (습도 높음) 물주기 중단
                elif curr_vpd < config.VPD_LOW_SAFE:
                    should_water = False
                    water_reason = f"VPD 낮음 ({curr_vpd:.2f} < {config.VPD_LOW_SAFE}) - 습도 충분"
                # 야간 모드 체크
                elif is_night:
                    should_water = False
                    water_reason = "야간 모드 - 물주기 금지"
                # 쿨타임 체크
                else:
                    time_since_last = time.time() - last_watering_time
                    if time_since_last < config.WATER_COOLDOWN:
                        should_water = False
                        water_reason = f"쿨타임 중 ({int(time_since_last)}초 < {config.WATER_COOLDOWN}초)"
            
            # 물주기 실행
            if should_water:
                app_logger.warning(f"[Auto] 💧 급수 시작: {water_reason}")
                
                # [안전한 급수 시퀀스]
                if send_cmd(ser_b, ser_b_lock, "M1"):  # 밸브 ON
                    with state_lock:
                        sys_state['valve_status'] = 'ON'
                    
                    # 설정된 시간만큼 대기 (물 주는 중)
                    time.sleep(config.WATERING_DURATION)
                    
                    # 밸브 OFF (반드시 꺼야 함!)
                    if send_cmd(ser_b, ser_b_lock, "M1"):  # 밸브 OFF (토글)
                        with state_lock:
                            sys_state['valve_status'] = 'OFF'
                        
                        last_watering_time = time.time()
                        # 급수량 계산 (점적스파이크 총 8개: 상추 5개 + 딸기 3개)
                        total_flow = (config.LETTUCE_DRIPS + config.STRAWBERRY_DRIPS) * config.DRIP_FLOW_RATE_LH
                        water_amount = (total_flow / 3600.0) * config.WATERING_DURATION  # L
                        watering_count_today += 1
                        total_water_used_today += water_amount
                        
                        # sys_state에 통계값 저장 (로그 기록용)
                        with state_lock:
                            sys_state['watering_count_today'] = watering_count_today
                            sys_state['water_used_today'] = total_water_used_today
                        
                        # 고급 기능: 물주기 효율성 모니터링
                        efficiency_info = f"오늘 {watering_count_today}회, 총 {total_water_used_today:.2f}L 사용"
                        app_logger.info(f"[Auto] ✅ 급수 완료: {water_amount:.2f}L | {efficiency_info} | 다음 급수까지 {config.WATER_COOLDOWN}초 대기")
                    else:
                        app_logger.error(f"[Auto] ❌ 밸브 OFF 명령 실패! 수동 확인 필요")
                        with state_lock:
                            sys_state['valve_status'] = 'OFF'
                else:
                    app_logger.error(f"[Auto] ❌ 밸브 ON 명령 실패! 급수 취소")
        
        # -------------------------------------------------------
        # ☀️ 조명 제어 로직 (일조량 기반)
        # -------------------------------------------------------
        if config.USE_AUTO_LED and not emergency_stop:
            # DLI 목표 달성 여부 확인
            dli = sys_state.get('dli', 0.0)
            need_light_boost = False
            light_reason = ""
            
            # 고급 기능: DLI 목표 달성률 계산
            dli_progress = (dli / config.TARGET_DLI_MAX) * 100 if config.TARGET_DLI_MAX > 0 else 0
            dli_progress = min(dli_progress, 100)  # 100% 초과 방지
            
            # 낮 시간대 체크
            if config.LED_ON_HOUR <= current_hour < config.LED_OFF_HOUR:
                # 자연광이 부족하면 LED 보조
                if curr_lux < config.MIN_LUX_THRESHOLD:
                    need_light_boost = True
                    light_reason = f"자연광 부족 ({curr_lux} Lux < {config.MIN_LUX_THRESHOLD})"
                # DLI 목표 미달 시 LED 보조
                elif dli < config.TARGET_DLI_MIN:
                    need_light_boost = True
                    light_reason = f"DLI 목표 미달 ({dli:.2f}/{config.TARGET_DLI_MAX} mol/m²/day, {dli_progress:.1f}%)"
            
            # LED 제어 (화이트 LED + 보라색 LED, 식물 생장 최적화)
            # 전략: White LED는 주 조명으로 사용, Purple LED는 DLI가 매우 낮을 때 보조로 추가
            # 타이밍: White LED와 Purple LED를 동시에 켜고 끄는 것이 식물 생장에 효과적
            # (일관된 광 환경 제공, 광형태형성 안정화)
            
            if need_light_boost:
                # White LED 켜기 (주 조명)
                if current_led_w == 'OFF':
                    # LED 페이드 인 (10분 동안 서서히 밝아짐)
                    if send_cmd(ser_b, ser_b_lock, "LED_FADE_ON"):
                        app_logger.info(f"[Auto] 💡 화이트 LED 페이드 인 시작: {light_reason} (10분 동안 서서히 밝아짐)")
                        with state_lock:
                            sys_state['led_w_status'] = 'ON'  # 페이드 시작 시 ON으로 표시
                            sys_state['led_w_brightness_pct'] = 100.0  # 목표 밝기 100%
                    else:
                        app_logger.warning(f"[Auto] 화이트 LED 페이드 인 시작 실패")
                
                # Purple LED 보조 사용 (DLI가 매우 낮을 때만)
                # White LED가 켜져 있고 DLI가 목표의 70% 미만일 때 Purple LED 추가
                if dli < config.TARGET_DLI_MIN * 0.7 and config.LED_PURPLE_BOOST:
                    if current_led_p == 'OFF':
                        # Purple LED 페이드 인 (White LED와 동시에 켜기)
                        if send_cmd(ser_b, ser_b_lock, "PURPLE_FADE_ON"):
                            app_logger.info(f"[Auto] 💜 보라색 LED 페이드 인 시작: DLI 매우 낮음 ({dli:.2f} < {config.TARGET_DLI_MIN * 0.7:.2f} mol/m²/day) - 보조 조명 활성화")
                            with state_lock:
                                sys_state['led_p_status'] = 'ON'
                                sys_state['led_p_brightness_pct'] = 100.0  # 목표 밝기 100% (최대 밝기 대비)
                        else:
                            app_logger.warning(f"[Auto] 보라색 LED 페이드 인 시작 실패")
                    # 이미 켜져 있으면 유지
                else:
                    # DLI가 충분하면 Purple LED 끄기 (White LED만 사용)
                    if current_led_p == 'ON':
                        if send_cmd(ser_b, ser_b_lock, "PURPLE_FADE_OFF"):
                            app_logger.info(f"[Auto] 💜 보라색 LED 페이드 아웃 시작: DLI 충분 ({dli:.2f} >= {config.TARGET_DLI_MIN * 0.7:.2f} mol/m²/day)")
                            with state_lock:
                                sys_state['led_p_status'] = 'OFF'
                                sys_state['led_p_brightness_pct'] = 0.0
            else:
                # LED 끄기 (밤 시간 또는 목표 달성, 페이드 아웃)
                # White LED와 Purple LED를 동시에 끄기 (일관된 광 환경 유지)
                if current_led_w == 'ON' and (current_hour >= config.LED_OFF_HOUR or current_hour < config.LED_ON_HOUR):
                    # White LED 페이드 아웃
                    if send_cmd(ser_b, ser_b_lock, "LED_FADE_OFF"):
                        app_logger.info(f"[Auto] 💡 화이트 LED 페이드 아웃 시작: 시간대 종료 또는 목표 달성 (10분 동안 서서히 꺼짐)")
                        with state_lock:
                            sys_state['led_w_status'] = 'OFF'  # 페이드 시작 시 OFF로 표시
                            sys_state['led_w_brightness_pct'] = 0.0  # 목표 밝기 0%
                    else:
                        app_logger.warning(f"[Auto] 화이트 LED 페이드 아웃 시작 실패")
                
                # Purple LED도 함께 끄기 (White LED가 꺼지면 Purple LED도 끄기)
                if current_led_p == 'ON':
                    if send_cmd(ser_b, ser_b_lock, "PURPLE_FADE_OFF"):
                        app_logger.info(f"[Auto] 💜 보라색 LED 페이드 아웃 시작: 화이트 LED 종료와 동시에 끄기")
                        with state_lock:
                            sys_state['led_p_status'] = 'OFF'
                            sys_state['led_p_brightness_pct'] = 0.0
        
        # -------------------------------------------------------
        # 🌬️ 환기 팬 제어 (VPD + 온습도 기반)
        # -------------------------------------------------------
        if config.USE_AUTO_FAN and not emergency_stop:
            fan_should_be_on = False
            fan_reason = ""
            
            # VPD 기반 제어 (우선순위 높음)
            if curr_vpd > config.VPD_FAN_ON:
                fan_should_be_on = True
                fan_reason = f"VPD 높음 ({curr_vpd:.2f} > {config.VPD_FAN_ON}) - 공기 순환 필요"
            elif curr_vpd < config.VPD_FAN_OFF:
                fan_should_be_on = False
                fan_reason = f"VPD 정상 ({curr_vpd:.2f} < {config.VPD_FAN_OFF})"
            # 온도/습도 기반 제어 (보조)
            elif curr_temp > config.TEMP_HIGH_LIMIT:
                fan_should_be_on = True
                fan_reason = f"온도 높음 ({curr_temp:.1f}°C > {config.TEMP_HIGH_LIMIT}°C)"
            elif curr_hum > config.HUM_HIGH_LIMIT:
                fan_should_be_on = True
                fan_reason = f"습도 높음 ({curr_hum:.1f}% > {config.HUM_HIGH_LIMIT}%)"
            
            # 팬 제어 실행
            if fan_should_be_on and current_fan == 'OFF':
                if send_cmd(ser_b, ser_b_lock, "FAN_ON"):
                    app_logger.info(f"[Auto] 🌬️ 팬 작동: {fan_reason}")
                    with state_lock:
                        sys_state['fan_status'] = 'ON'
                else:
                    app_logger.warning(f"[Auto] 팬 켜기 명령 실패: {fan_reason}")
            elif not fan_should_be_on and current_fan == 'ON':
                if send_cmd(ser_b, ser_b_lock, "FAN_OFF"):
                    app_logger.info(f"[Auto] 🌬️ 팬 정지: {fan_reason}")
                    with state_lock:
                        sys_state['fan_status'] = 'OFF'
                else:
                    app_logger.warning(f"[Auto] 팬 끄기 명령 실패")
        
        # -------------------------------------------------------
        # 🪟 커튼 제어 (VPD 기반) - 스테퍼 모터
        # -------------------------------------------------------
        if config.USE_AUTO_CURTAIN and not emergency_stop:
            # VPD가 낮으면 (습도 높음) 커튼 열기, VPD가 높으면 (건조) 커튼 닫기
            target_curtain_state = None
            
            if curr_vpd < config.VPD_CURTAIN_OPEN:
                target_curtain_state = "OPEN"
            elif curr_vpd > config.VPD_CURTAIN_CLOSE:
                target_curtain_state = "CLOSED"
            
            # 커튼 상태 변경이 필요한 경우
            if target_curtain_state and target_curtain_state != curtain_state:
                # 스텝 수 계산 (방향 고려)
                if target_curtain_state == "OPEN":
                    # 열기: CCW면 양수, CW면 음수
                    steps = config.CURTAIN_STEPS_OPEN if config.CURTAIN_OPEN_DIRECTION == "CCW" else -config.CURTAIN_STEPS_OPEN
                    cmd = f"CURTAIN_OPEN:{steps}"
                    reason = f"VPD 낮음 ({curr_vpd:.2f} < {config.VPD_CURTAIN_OPEN}) - 습도 높음"
                else:  # CLOSED
                    # 닫기: 열기의 반대 방향
                    steps = -config.CURTAIN_STEPS_CLOSE if config.CURTAIN_OPEN_DIRECTION == "CCW" else config.CURTAIN_STEPS_CLOSE
                    cmd = f"CURTAIN_CLOSE:{steps}"
                    reason = f"VPD 높음 ({curr_vpd:.2f} > {config.VPD_CURTAIN_CLOSE}) - 건조"
                
                # 명령 전송
                if send_cmd(ser_b, ser_b_lock, cmd):
                    curtain_state = target_curtain_state
                    app_logger.info(f"[Auto] 🪟 커튼 {target_curtain_state}: {reason} (스텝: {steps})")
                    with state_lock:
                        sys_state['curtain_status'] = target_curtain_state
                else:
                    app_logger.warning(f"[Auto] 🪟 커튼 제어 명령 실패: {cmd}")
        
        # CPU 과부하 방지 (1초 휴식)
        time.sleep(1)

def send_cmd(ser, lock, cmd):
    """
    아두이노로 명령 전송 (스레드 안전)
    Returns: True if successful, False otherwise
    """
    if not ser or not ser.is_open:
        app_logger.warning(f"[Auto] ⚠️ 시리얼 포트가 열려있지 않습니다.")
        return False
        
    with lock:
        try:
            ser.write((cmd + '\n').encode())
            ser.flush()  # 버퍼 강제 전송
            time.sleep(0.1)  # 전송 안정성 확보
            return True
        except serial.SerialException as e:
            app_logger.error(f"[Auto] ⚠️ 시리얼 통신 오류 (명령: {cmd}): {e}")
            return False
        except (OSError, IOError) as e:
            app_logger.error(f"[Auto] ⚠️ I/O 오류 (명령: {cmd}): {e}")
            return False
        except Exception as e:
            app_logger.error(f"[Auto] ⚠️ 예상치 못한 오류 (명령: {cmd}): {e}")
            return False
