# main.py
import serial
import time
import threading
import queue
import os
from datetime import datetime

# 분리한 모듈들 import
import config
import logger
import automation

# 전역 객체
data_queue = queue.Queue()
stop_event = threading.Event()
ser_b_lock = threading.Lock()

# 공유 상태 (Dictionary는 Mutable이라 다른 모듈에서 수정하면 여기서도 반영됨)
sys_state = {
    'soil_pct': 100, 
    'valve_status': 'OFF', 
    'last_water_time': 0
}

def main():
    try:
        ser_a = serial.Serial(config.PORT_A, config.BAUD_RATE, timeout=1)
        ser_b = serial.Serial(config.PORT_B, config.BAUD_RATE, timeout=1)
        ser_a.flushInput()
        print(f"System Online. Log Dir: {config.LOG_DIR}")
    except Exception as e:
        print(f"Serial Connection Failed: {e}")
        return

    # --- 스레드 생성 및 실행 ---
    # args로 필요한 객체들을 넘겨줍니다.
    t_log = threading.Thread(
        target=logger.logger_thread_func, 
        args=(data_queue, stop_event)
    )
    
    t_auto = threading.Thread(
        target=automation.automation_thread_func, 
        args=(ser_b, ser_b_lock, sys_state, stop_event, data_queue)
    )
    
    t_log.start()
    t_auto.start()

    try:
        while True:
            # Board A 리스닝 (Main Thread는 통신 중계에 집중)
            if ser_a.in_waiting > 0:
                # 시리얼 데이터를 읽고(readline) -> 디코딩(decode) -> 공백제거(strip)를 한 번에 처리
                line = ser_a.readline().decode('utf-8', errors='ignore').strip()                
                
                if line.startswith("DATA,"):
                    parts = line.split(',')
                    if len(parts) == 7:
                        vals = parts[1:] 
                        sys_state['soil_pct'] = int(vals[3]) # 상태 업데이트
                        
                        # 로그 큐에 넣기
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        log_row = [timestamp] + vals + [sys_state['valve_status'], '']
                        data_queue.put(log_row)

                elif line.startswith("CMD_"):
                    cmd = line.split("_")[1]
                    print(f"User Command: {cmd}")
                    
                    with ser_b_lock:
                        ser_b.write((cmd + "\n").encode())
                        
                    if cmd == 'M1':
                        sys_state['valve_status'] = 'ON' if sys_state['valve_status'] == 'OFF' else 'OFF'
                        
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    data_queue.put([timestamp] + ['-']*6 + [sys_state['valve_status'], f"User_{cmd}"])

                elif line == "SYS_OFF":
                    print("Shutdown...")
                    stop_event.set()
                    os.system("sudo shutdown -h now")
                    break
            
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nStopping System...")
        stop_event.set()
    finally:
        t_log.join()
        t_auto.join()
        ser_a.close()
        ser_b.close()
        print("System Offline.")

if __name__ == "__main__":
    main()