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

# ==========================================
# 📡 스레드: Board A (센서 수신 -> 큐 전송)
# ==========================================
# main.py 내부의 serial_thread_A 함수 수정

# main.py 내부의 serial_thread_A 함수를 이것으로 덮어씌우세요.

def serial_thread_A(ser_a, stop_event, sys_state, state_lock, data_queue):
    """
    [아두이노 코드 분석 기반 수정 완료]
    - DATA... : 센서 데이터 처리
    - CMD_M6  : 카메라 촬영 (메뉴 7번째)
    - SYS_OFF : 시스템 종료 (메뉴 8번째)
    """
    print(f"[Thread A] Board A 통신 리스너 가동 (CMD_M6 대기중)")
    
    while not stop_event.is_set():
        try:
            if ser_a and ser_a.in_waiting:
                # 데이터 읽기 및 공백 제거
                raw_line = ser_a.readline()
                try:
                    line = raw_line.decode('utf-8', errors='ignore').strip()
                except:
                    continue 

                if not line: continue
                
                # 디버깅: 실제로 뭐가 들어오는지 눈으로 확인
                # print(f"[RX] {line}") 

                # ==========================================
                # [Case 1] 카메라 테스트 (Menu Index 6)
                # 아두이노 코드: Serial.print("CMD_M"); Serial.println(6);
                # ==========================================
                if line == "CMD_M6":
                    print(f"[Main] 📸 카메라 수동 촬영 명령(CMD_M6) 수신!")
                    camera.take_picture("User_Manual")

                # ==========================================
                # [Case 2] 시스템 종료 (Menu Index 7)
                # 아두이노 코드: Serial.println("SYS_OFF");
                # ==========================================
                elif line == "SYS_OFF":
                    print(f"[Main] 🛑 아두이노에서 종료 요청(SYS_OFF) 수신.")
                    stop_event.set() # 프로그램 안전 종료

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
                            except ValueError:
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

                # ==========================================
                # [Case 4] 그 외 메뉴 명령 (CMD_M0 ~ CMD_M5)
                # ==========================================
                elif line.startswith("CMD_M"):
                    cmd_idx = line.replace("CMD_M", "")
                    print(f"[Main] ⚠️ 아직 연결되지 않은 메뉴 명령: {cmd_idx}번")
                    # 필요하면 여기서 Board B로 제어 신호를 넘길 수도 있습니다.

        except Exception as e:
            print(f"[Thread A Error] {e}")
            time.sleep(1)

# ==========================================
# 🎮 메인 실행 로직
# ==========================================
def main():
    print("=== 🌱 Smart Farm System (Queue & Logger Integrated) ===")
    
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

    # Board A (센서/OLED)
    try:
        ser_a = serial.Serial(config.PORT_A, config.BAUD_RATE, timeout=1)
        ser_a.flush()
        print(f"[Main] Board A 연결 성공")
    except Exception as e:
        print(f"[Main] ⚠️ Board A 연결 실패: {e}")

    # Board B (제어)
    try:
        ser_b = serial.Serial(config.PORT_B, config.BAUD_RATE, timeout=1)
        ser_b.flush()
        print(f"[Main] Board B 연결 성공")
    except Exception as e:
        print(f"[Main] ⚠️ Board B 연결 실패: {e}")

    ser_b_lock = threading.Lock()

    # 4. 스레드 시작
    threads = []

    # (A) 로거 스레드 (가장 먼저 대기)
    t_logger = threading.Thread(target=logger.logger_thread_func, args=(log_queue, stop_event))
    t_logger.start()
    threads.append(t_logger)

    # (B) 센서 수신 스레드 (큐 전달)
    if ser_a:
        t_sensor = threading.Thread(target=serial_thread_A, args=(ser_a, stop_event, sys_state, state_lock, log_queue))
        t_sensor.start()
        threads.append(t_sensor)

    # (C) 자동화 스레드
    if ser_b:
        t_auto = threading.Thread(target=automation.automation_loop, args=(stop_event, sys_state, ser_b, ser_b_lock))
        t_auto.start()
        threads.append(t_auto)

    # (D) 카메라 스레드
    t_cam = threading.Thread(target=camera.camera_loop, args=(stop_event,))
    t_cam.start()
    threads.append(t_cam)

    print("=== System Running. (Logging via Queue) ===")

    # 5. 메인 루프 (OLED 업데이트 담당)
    try:
        last_ui_update = 0
        
        while True:
            # 5초마다 Board A로 상태(시간) 전송
            if time.time() - last_ui_update > 5.0:
                now = datetime.now()
                
                with state_lock:
                    v = sys_state.get('valve_status', 'OFF')
                    f = sys_state.get('fan_status', 'OFF')
                    w = sys_state.get('led_w_status', 'OFF')
                    p = sys_state.get('led_p_status', 'OFF')
                
                # 프로토콜: STATE,Valve,Fan,LedW,LedP,Hour,Min
                msg = f"STATE,{v},{f},{w},{p},{now.hour},{now.minute}\n"
                
                if ser_a and ser_a.is_open:
                    try:
                        ser_a.write(msg.encode())
                    except Exception as e:
                        print(f"[Main Error] UI 전송 실패: {e}")
                
                last_ui_update = time.time()

            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[Main] 종료 요청! 정리 중...")
        stop_event.set()
        
        for t in threads:
            t.join()
            
        if ser_a: ser_a.close()
        if ser_b: ser_b.close()
        print("[Main] 종료 완료.")

if __name__ == "__main__":
    main()