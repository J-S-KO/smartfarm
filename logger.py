# logger.py
import os
import csv
import queue
from datetime import datetime
import config  # 설정 파일 불러오기

# 큐 크기 제한 (메모리 보호)
MAX_QUEUE_SIZE = 1000

def logger_thread_func(data_queue, stop_event):
    try:
        if not os.path.exists(config.LOG_DIR):
            os.makedirs(config.LOG_DIR, exist_ok=True)
    except OSError as e:
        print(f"[Logger Error] 로그 폴더 생성 실패: {e}")
        return
        
    print("[Logger] Service Started.")
    
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10
    
    while not stop_event.is_set():
        try:
            # 큐 크기 체크 (메모리 보호)
            if data_queue.qsize() > MAX_QUEUE_SIZE:
                print(f"[Logger] ⚠️ 큐가 가득 참 ({data_queue.qsize()}개). 오래된 데이터 버림.")
                # 오래된 데이터 제거
                try:
                    for _ in range(100):  # 100개씩 제거
                        data_queue.get_nowait()
                        data_queue.task_done()
                except queue.Empty:
                    pass
                continue
            
            # 큐에서 데이터 꺼내기 (1초 대기)
            log_item = data_queue.get(timeout=1)
            
            today_str = datetime.now().strftime('%Y-%m-%d')
            filename = os.path.join(config.LOG_DIR, f"smartfarm_log_{today_str}.csv")
            file_exists = os.path.isfile(filename)
            
            # 파일 쓰기 (에러 처리 강화)
            try:
                with open(filename, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # 헤더가 없으면 생성
                    if not file_exists:
                        writer.writerow(['Timestamp', 'Temp', 'Hum', 'Soil_Raw', 'Soil_Pct', 'Lux', 'VPD', 'Valve', 'Note'])
                    writer.writerow(log_item)
                    f.flush()  # 즉시 디스크에 쓰기
                
                consecutive_errors = 0  # 성공 시 에러 카운터 리셋
                data_queue.task_done()
                
            except (OSError, IOError) as e:
                consecutive_errors += 1
                print(f"[Logger Error] 파일 쓰기 실패 (연속 {consecutive_errors}회): {e}")
                data_queue.task_done()  # 실패해도 task_done 호출
                
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(f"[Logger] ⚠️ 연속 {MAX_CONSECUTIVE_ERRORS}회 오류 발생. 로깅 일시 중지.")
                    time.sleep(60)  # 1분 대기 후 재시도
                    consecutive_errors = 0
                else:
                    time.sleep(1)  # 짧은 대기 후 재시도
                    
        except queue.Empty:
            continue
        except Exception as e:
            consecutive_errors += 1
            print(f"[Logger Error] 예상치 못한 오류 (연속 {consecutive_errors}회): {e}")
            if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                print(f"[Logger] ⚠️ 심각한 오류로 인해 로깅 일시 중지.")
                time.sleep(60)
                consecutive_errors = 0