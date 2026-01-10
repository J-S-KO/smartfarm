"""
유틸리티 함수 모듈
- 시리얼 재연결 로직
- 설정 검증
"""
import serial
import time
import config

def reconnect_serial(port, baud_rate, max_retries=5, retry_delay=5):
    """
    시리얼 포트 재연결 시도
    """
    import time  # 함수 내에서 사용하므로 import 확인
    
    for i in range(max_retries):
        try:
            # 1. 연결 시도
            ser = serial.Serial(port, baud_rate, timeout=1)
            
            # [추가할 부분] 2. 연결은 됐지만, 아두이노가 재부팅 중이니 기다려줌
            time.sleep(2)  
            
            # 3. 버퍼 비우기 (flush 대신 reset_input_buffer 권장)
            ser.reset_input_buffer()
            
            print(f"[Utils] ✅ 시리얼 포트 재연결 성공: {port}")
            return ser
            
        except serial.SerialException as e:
            # 여기는 '연결 자체를 못했을 때' 대기하는 곳입니다.
            print(f"[Utils] ⚠️ 재연결 시도 {i+1}/{max_retries} 실패 ({port}): {e}")
            if i < max_retries - 1:
                time.sleep(retry_delay) # 이건 5초 그대로 둬도 됩니다.
                
        except Exception as e:
            print(f"[Utils] ⚠️ 예상치 못한 오류 ({port}): {e}")
            if i < max_retries - 1:
                time.sleep(retry_delay)
    
    print(f"[Utils] ❌ 시리얼 포트 재연결 실패 (최대 시도 횟수 초과): {port}")
    return None
    
def validate_config():
    """
    config.py 설정값 유효성 검증
    Returns: (is_valid, error_messages)
    """
    errors = []
    
    # 시리얼 통신 설정
    if not hasattr(config, 'PORT_A') or not config.PORT_A:
        errors.append("PORT_A가 설정되지 않았습니다.")
    if not hasattr(config, 'PORT_B') or not config.PORT_B:
        errors.append("PORT_B가 설정되지 않았습니다.")
    if not hasattr(config, 'BAUD_RATE') or config.BAUD_RATE <= 0:
        errors.append("BAUD_RATE가 유효하지 않습니다.")
    
    # 자동 급수 설정
    if hasattr(config, 'SOIL_TRIGGER_PCT'):
        if not (0 <= config.SOIL_TRIGGER_PCT <= 100):
            errors.append(f"SOIL_TRIGGER_PCT는 0-100 사이여야 합니다. (현재: {config.SOIL_TRIGGER_PCT})")
    if hasattr(config, 'WATERING_DURATION'):
        if config.WATERING_DURATION <= 0:
            errors.append(f"WATERING_DURATION은 양수여야 합니다. (현재: {config.WATERING_DURATION})")
    if hasattr(config, 'WATER_COOLDOWN'):
        if config.WATER_COOLDOWN < 0:
            errors.append(f"WATER_COOLDOWN은 0 이상이어야 합니다. (현재: {config.WATER_COOLDOWN})")
    
    # 야간 모드 설정
    if hasattr(config, 'NIGHT_START_HOUR') and hasattr(config, 'NIGHT_END_HOUR'):
        if not (0 <= config.NIGHT_START_HOUR < 24) or not (0 <= config.NIGHT_END_HOUR < 24):
            errors.append(f"시간 설정은 0-23 사이여야 합니다. (NIGHT_START: {config.NIGHT_START_HOUR}, NIGHT_END: {config.NIGHT_END_HOUR})")
    
    # 조명 설정
    if hasattr(config, 'LED_ON_HOUR') and hasattr(config, 'LED_OFF_HOUR'):
        if not (0 <= config.LED_ON_HOUR < 24) or not (0 <= config.LED_OFF_HOUR < 24):
            errors.append(f"LED 시간 설정은 0-23 사이여야 합니다. (ON: {config.LED_ON_HOUR}, OFF: {config.LED_OFF_HOUR})")
    
    # 환기 설정
    if hasattr(config, 'TEMP_HIGH_LIMIT'):
        if config.TEMP_HIGH_LIMIT < -50 or config.TEMP_HIGH_LIMIT > 100:
            errors.append(f"TEMP_HIGH_LIMIT는 -50~100 사이여야 합니다. (현재: {config.TEMP_HIGH_LIMIT})")
    if hasattr(config, 'HUM_HIGH_LIMIT'):
        if not (0 <= config.HUM_HIGH_LIMIT <= 100):
            errors.append(f"HUM_HIGH_LIMIT는 0-100 사이여야 합니다. (현재: {config.HUM_HIGH_LIMIT})")
    
    # 카메라 설정
    if hasattr(config, 'CAM_INTERVAL_MIN'):
        if config.CAM_INTERVAL_MIN <= 0:
            errors.append(f"CAM_INTERVAL_MIN은 양수여야 합니다. (현재: {config.CAM_INTERVAL_MIN})")
    
    # 경로 설정
    if hasattr(config, 'LOG_DIR') and not config.LOG_DIR:
        errors.append("LOG_DIR가 설정되지 않았습니다.")
    if hasattr(config, 'IMG_DIR') and not config.IMG_DIR:
        errors.append("IMG_DIR가 설정되지 않았습니다.")
    
    is_valid = len(errors) == 0
    return is_valid, errors

