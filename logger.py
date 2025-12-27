# logger.py
import os
import csv
import queue
from datetime import datetime
import config  # 설정 파일 불러오기

def logger_thread_func(data_queue, stop_event):
    if not os.path.exists(config.LOG_DIR):
        os.makedirs(config.LOG_DIR)
        
    print("[Logger] Service Started.")
    
    while not stop_event.is_set():
        try:
            # 큐에서 데이터 꺼내기 (1초 대기)
            log_item = data_queue.get(timeout=1)
            
            today_str = datetime.now().strftime('%Y-%m-%d')
            filename = os.path.join(config.LOG_DIR, f"smartfarm_log_{today_str}.csv")
            file_exists = os.path.isfile(filename)
            
            with open(filename, 'a', newline='') as f:
                writer = csv.writer(f)
                # 헤더가 없으면 생성
                if not file_exists:
                    writer.writerow(['Timestamp', 'Temp', 'Hum', 'Soil_Raw', 'Soil_Pct', 'Lux', 'VPD', 'Valve', 'Note'])
                writer.writerow(log_item)
                
            data_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"[Logger Error] {e}")