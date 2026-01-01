import time
import threading
import queue  # 큐 모듈 추가
import serial
import os
from datetime import datetime

# 사용자 모듈 임포트
import config
import automation
import camera
import logger  # 로거 모듈 임포트
import utils  # 유틸리티 함수 (재연결, 검증)
import logging  # 로깅 시스템

# ==========================================
# 📡 스레드: Board A (센서 수신 -> 큐 전송)
# ==========================================
# main.py 내부의 serial_thread_A 함수 수정

# main.py 내부의 serial_thread_A 함수를 이것으로 덮어씌우세요.

def serial_thread_A(ser_a, stop_event, sys_state, state_lock, data_queue, camera_thread, app_logger):
    """
    Board A 통신 리스너 스레드
    - DATA... : 센서 데이터 처리
    - CMD_M6  : 카메라 촬영 (메뉴 7번째)
    - SYS_OFF : 시스템 종료 (메뉴 8번째)
    """
    app_logger.info(f"[Thread A] Board A 통신 리스너 가동 (ser_a={ser_a}, is_open={ser_a.is_open if ser_a else 'N/A'})")
    
    if not ser_a:
        app_logger.warning("[Thread A] ⚠️ Board A 시리얼 포트가 연결되지 않았습니다.")
        return
    
    if not ser_a.is_open:
        app_logger.error("[Thread A] ⚠️ Board A 시리얼 포트가 열려있지 않습니다.")
        return
    
    while not stop_event.is_set():
        try:
            # CPU 사용 최적화: 데이터가 없을 때는 짧게 대기
            if not ser_a.in_waiting:
                time.sleep(0.1)  # 데이터 없을 때 CPU 부하 감소
                continue
                
            # 데이터 읽기 및 공백 제거
            raw_line = ser_a.readline()
            try:
                line = raw_line.decode('utf-8', errors='ignore').strip()
            except (UnicodeDecodeError, AttributeError) as e:
                app_logger.warning(f"[Thread A] 디코딩 오류: {e}")
                continue 

            if not line: 
                continue
                
            # 디버깅: 실제로 뭐가 들어오는지 눈으로 확인
            app_logger.debug(f"[RX] {line}") 

            # ==========================================
            # [Case 1] 카메라 테스트 (Menu Index 6)
            # 아두이노 코드: Serial.print("CMD_M"); Serial.println(6);
            # ==========================================
            if line == "CMD_M6":
                app_logger.info("[Thread A] 📸 사용자 수동 촬영 요청(CMD_M6) 수신!")
                
                # camera_thread가 살아있는지 확인 후 '방아쇠'만 당김
                if camera_thread and camera_thread.is_alive():
                    app_logger.info("[Thread A] 카메라 스레드 활성 상태 확인, 촬영 트리거")
                    camera_thread.trigger_manual_capture() 
                else:
                    app_logger.warning(f"[Thread A] 카메라 스레드 응답 없음 (camera_thread={camera_thread}, is_alive={camera_thread.is_alive() if camera_thread else 'N/A'})")

            # ==========================================
            # [Case 2] 시스템 종료 (Menu Index 7)
            # 아두이노 코드: Serial.println("SYS_OFF");
            # ==========================================
            elif line == "SYS_OFF":
                app_logger.info("[Thread A] 🛑 시스템 종료 요청 수신. 라즈베리파이 종료 중...")
                
                # 라즈베리파이 자체를 종료
                os.system("sudo shutdown -h now")

            # ==========================================
            # [Case 3] 센서 데이터 (DATA로 시작)
            # ==========================================
            elif line.startswith("DATA"):
                parts = line.split(',')
                if len(parts) >= 6:
                    with state_lock:
                        try:
                            sys_state['temp'] = float(parts[1])
                            sys_state['hum'] = float(parts[2])
                            sys_state['soil_pct'] = int(parts[4])
                            sys_state['lux'] = int(parts[5])
                            current_valve = sys_state.get('valve_status', 'OFF')
                        except ValueError as ve:
                            app_logger.warning(f"[Thread A] 센서 데이터 파싱 오류: {ve}, line={line}")
                            continue
                    
                    # 로그 큐 전송
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # parts 인덱스 에러 방지용 안전 장치
                    p3 = parts[3] if len(parts)>3 else "0"
                    p6 = parts[6] if len(parts)>6 else "0"
                    
                    log_data = [
                        timestamp, parts[1], parts[2], p3, 
                        parts[4], parts[5], p6, current_valve, ""
                    ]
                    data_queue.put(log_data)
                    app_logger.debug(f"[Thread A] 센서 데이터 큐에 추가: Temp={parts[1]}, Hum={parts[2]}, Soil={parts[4]}%")

            # ==========================================
            # [Case 4] 그 외 메뉴 명령 (CMD_M0 ~ CMD_M5)
            # ==========================================
            elif line.startswith("CMD_M"):
                cmd_idx = line.replace("CMD_M", "")
                app_logger.info(f"[Thread A] 메뉴 명령 수신: {cmd_idx}번")
                # 필요하면 여기서 Board B로 제어 신호를 넘길 수도 있습니다.

        except serial.SerialException as e:
            app_logger.error(f"[Thread A] 시리얼 통신 오류: {e}")
            time.sleep(2)  # 재연결 대기 시간 증가
        except (OSError, IOError) as e:
            app_logger.error(f"[Thread A] I/O 오류: {e}")
            time.sleep(2)
        except Exception as e:
            app_logger.error(f"[Thread A] 예상치 못한 오류: {e}")
            time.sleep(1)

# ==========================================
# 🎮 메인 실행 로직
# ==========================================
def main():
    # 로깅 시스템 초기화
    file_handler = logging.FileHandler(os.path.join(config.BASE_DIR, 'smartfarm.log'))
    file_handler.setLevel(logging.DEBUG)  # 파일에는 DEBUG 레벨까지 저장
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # 콘솔에는 INFO 레벨만 출력
    
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)
    
    app_logger.info("=== 🌱 Smart Farm System (Queue & Logger Integrated) ===")
    
    # 설정 검증
    is_valid, errors = utils.validate_config()
    if not is_valid:
        app_logger.error("❌ 설정 검증 실패:")
        for error in errors:
            app_logger.error(f"  - {error}")
        print("\n설정 파일(config.py)을 확인하고 수정해주세요.")
        return
    
    app_logger.info("✅ 설정 검증 완료")
    
    # 1. 데이터 통신용 큐 생성
    log_queue = queue.Queue()
    
    # 2. 공유 데이터 저장소
    sys_state = {
        'temp': 0.0, 'hum': 0.0, 'soil_pct': 0, 'lux': 0,
        'valve_status': 'OFF',
        'fan_status': 'OFF',
        'led_w_status': 'OFF',
        'led_p_status': 'OFF'
    }
    state_lock = threading.Lock()
    stop_event = threading.Event()

    # 3. 시리얼 연결
    ser_a = None
    ser_b = None

    # Board A (센서/OLED) - 재연결 로직 포함
    ser_a = None
    try:
        ser_a = serial.Serial(config.PORT_A, config.BAUD_RATE, timeout=1)
        time.sleep(2)  # 아두이노 재부팅 대기
        ser_a.reset_input_buffer()  # 버퍼 초기화
        ser_a.reset_output_buffer()
        app_logger.info(f"[Main] Board A 연결 성공: {config.PORT_A}")
    except Exception as e:
        app_logger.warning(f"[Main] ⚠️ Board A 연결 실패: {e}")
        app_logger.info("재연결 시도 중...")
        ser_a = utils.reconnect_serial(config.PORT_A, config.BAUD_RATE)
        if ser_a:
            app_logger.info(f"[Main] Board A 재연결 성공: {config.PORT_A}")

    # Board B (제어) - 재연결 로직 포함
    ser_b = None
    try:
        ser_b = serial.Serial(config.PORT_B, config.BAUD_RATE, timeout=1)
        time.sleep(2)  # 아두이노 재부팅 대기
        ser_b.reset_input_buffer()  # 버퍼 초기화
        ser_b.reset_output_buffer()
        app_logger.info(f"[Main] Board B 연결 성공: {config.PORT_B}")
    except Exception as e:
        app_logger.warning(f"[Main] ⚠️ Board B 연결 실패: {e}")
        app_logger.info("재연결 시도 중...")
        ser_b = utils.reconnect_serial(config.PORT_B, config.BAUD_RATE)
        if ser_b:
            app_logger.info(f"[Main] Board B 재연결 성공: {config.PORT_B}")

    ser_b_lock = threading.Lock()

    # 4. 스레드 시작
    threads = []

    # (A) 로거 스레드 (가장 먼저 대기)
    t_logger = threading.Thread(target=logger.logger_thread_func, args=(log_queue, stop_event))
    t_logger.start()
    threads.append(t_logger)

    # (B) 카메라 스레드 (먼저 생성하여 다른 스레드에 전달 가능하도록)
    t_cam = camera.CameraThread()
    t_cam.daemon = True  # 메인 프로세스 종료 시 함께 종료
    t_cam.start()
    threads.append(t_cam)
    app_logger.info(f"[Main] 카메라 스레드 시작됨 (is_alive={t_cam.is_alive()})")

    # (C) 센서 수신 스레드 (큐 전달, camera_thread 전달)
    if ser_a:
        t_sensor = threading.Thread(target=serial_thread_A, args=(ser_a, stop_event, sys_state, state_lock, log_queue, t_cam, app_logger), daemon=True)
        t_sensor.start()
        threads.append(t_sensor)
    else:
        app_logger.warning("[Main] ⚠️ Board A 미연결: 센서 수신 스레드 시작 안 함")

    # (D) 자동화 스레드
    if ser_b:
        t_auto = threading.Thread(target=automation.automation_loop, args=(stop_event, sys_state, ser_b, ser_b_lock, state_lock), daemon=True)
        t_auto.start()
        threads.append(t_auto)
    else:
        app_logger.warning("[Main] ⚠️ Board B 미연결: 자동화 스레드 시작 안 함")

    app_logger.info("=== System Running. (Logging via Queue) ===")

    # 5. 메인 루프 (OLED 업데이트 담당)
    try:
        last_ui_update = 0
        app_logger.info("[Main] 메인 루프 시작 (Time Sync 가동)")

        while True:
            # 2초마다 (5초는 좀 깁니다, 2초 추천) Board A로 상태(시간) 전송
            # 아두이노는 이 신호가 끊기면 멈춘 것으로 간주할 수도 있습니다.
            if time.time() - last_ui_update > 2.0:
                now = datetime.now()
                
                # state_lock이 있다면 사용, 없다면 그냥 가져옴
                # (Queue 방식이라면 sys_state 딕셔너리가 전역변수인지 확인 필요)
                v = sys_state.get('valve_status', 'OFF')
                f = sys_state.get('fan_status', 'OFF')
                w = sys_state.get('led_w_status', 'OFF')
                p = sys_state.get('led_p_status', 'OFF')
                
                # 프로토콜: STATE,Valve,Fan,LedW,LedP,Hour,Min
                msg = f"STATE,{v},{f},{w},{p},{now.hour},{now.minute}\n"
                
                # Board A로 상태 전송
                if ser_a and ser_a.is_open:
                    try:
                        ser_a.write(msg.encode())
                        ser_a.flush()  # 버퍼 강제 전송
                        app_logger.debug(f"[Tx] {msg.strip()}") # 디버깅용
                    except Exception as e:
                        app_logger.error(f"[Main] UI 전송 실패: {e}")
                else:
                    # 연결이 안 되어 있다면 로그 찍기
                    app_logger.warning(f"[Main] Board A 연결 안됨 (ser_a={ser_a}, is_open={ser_a.is_open if ser_a else 'N/A'}), 시간 전송 불가")
                
                last_ui_update = time.time()

            time.sleep(0.1)
            
    except KeyboardInterrupt:
        app_logger.info("\n[Main] 종료 요청! 정리 중...")
        stop_event.set()
        
        # 카메라 스레드 정리
        if t_cam and t_cam.is_alive():
            t_cam.stop()
        
        # 스레드 종료 대기 (타임아웃 적용)
        for t in threads:
            t.join(timeout=5.0)  # 최대 5초 대기
            if t.is_alive():
                app_logger.warning(f"[Main] ⚠️ 스레드 {t.name}가 정상 종료되지 않았습니다.")
            
        # 시리얼 포트 안전하게 닫기
        if ser_a and ser_a.is_open:
            try:
                ser_a.close()
                app_logger.info("[Main] Board A 시리얼 포트 닫힘")
            except Exception as e:
                app_logger.error(f"[Main] Board A 닫기 오류: {e}")
                
        if ser_b and ser_b.is_open:
            try:
                ser_b.close()
                app_logger.info("[Main] Board B 시리얼 포트 닫힘")
            except Exception as e:
                app_logger.error(f"[Main] Board B 닫기 오류: {e}")
                
        app_logger.info("[Main] 종료 완료.")

if __name__ == "__main__":
    main()