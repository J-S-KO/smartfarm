# automation.py
import time
import config
from datetime import datetime

def automation_thread_func(ser_b, ser_b_lock, sys_state, stop_event, data_queue):
    print("[Automation] Service Started.")
    
    while not stop_event.is_set():
        current_soil = sys_state['soil_pct']
        now = time.time()
        
        # 급수 조건 체크
        if current_soil < config.SOIL_TRIGGER_PCT and (now - sys_state['last_water_time'] > config.WATER_COOLDOWN):
            print(f"[Auto] Dry Soil Detected ({current_soil}%) - Watering...")
            
            # 1. 밸브 열기
            with ser_b_lock:
                ser_b.write(b"M1\n")
                sys_state['valve_status'] = 'ON'
            
            # 로그 기록 (시작)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data_queue.put([timestamp, '-', '-', '-', current_soil, '-', '-', 'ON', 'Auto_Start'])
            
            time.sleep(config.WATERING_DURATION)
            
            # 2. 밸브 닫기
            with ser_b_lock:
                ser_b.write(b"M1\n")
                sys_state['valve_status'] = 'OFF'
            
            sys_state['last_water_time'] = time.time()
            print("[Auto] Watering Finished.")
            
            # 로그 기록 (종료)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data_queue.put([timestamp, '-', '-', '-', current_soil, '-', '-', 'OFF', f'Auto_End_{config.WATERING_DURATION}s'])
            
        time.sleep(1) # 1초마다 감시