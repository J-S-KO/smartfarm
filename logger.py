# logger.py
import os
import csv
import queue
import time
import logging
import shutil
from datetime import datetime
import config  # 설정 파일 불러오기

# 로거 인스턴스 생성 (다른 모듈에서 사용 가능)
app_logger = logging.getLogger('smartfarm')

# 큐 크기 제한 (메모리 보호)
MAX_QUEUE_SIZE = 1000

def get_log_path():
    """
    월별 폴더 구조로 로그 파일 경로 생성
    Returns: (log_dir, filename)
    """
    now = datetime.now()
    month_dir = now.strftime('%Y-%m')  # YYYY-MM 형식
    log_dir = os.path.join(config.LOG_DIR, month_dir)
    
    # 월별 폴더 생성
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        app_logger.error(f"[Logger] 월별 폴더 생성 실패: {e}")
        # 폴더 생성 실패 시 기본 폴더 사용
        log_dir = config.LOG_DIR
        os.makedirs(log_dir, exist_ok=True)
    
    today_str = now.strftime('%Y-%m-%d')
    filename = os.path.join(log_dir, f"smartfarm_log_{today_str}.csv")
    
    return log_dir, filename

def get_image_path(filename, tag="Auto"):
    """
    이미지 파일 경로 생성
    - Auto: 월별 폴더 구조 (images/YYYY-MM/)
    - User: 수동 촬영 폴더 (images/manual/)
    Args:
        filename: 이미지 파일명 (예: "2026-01-02_12-30-00_Auto.jpg")
        tag: 촬영 타입 ("Auto" 또는 "User")
    Returns: (image_dir, filepath)
    """
    if tag == "User":
        # 수동 촬영: images/manual/ 폴더에 저장
        image_dir = os.path.join(config.IMG_DIR, "manual")
    else:
        # 자동 촬영: 월별 폴더 구조 (images/YYYY-MM/)
        now = datetime.now()
        month_dir = now.strftime('%Y-%m')  # YYYY-MM 형식
        image_dir = os.path.join(config.IMG_DIR, month_dir)
    
    # 폴더 생성
    try:
        os.makedirs(image_dir, exist_ok=True)
    except OSError as e:
        app_logger.error(f"[Logger] 이미지 폴더 생성 실패: {e}")
        # 폴더 생성 실패 시 기본 폴더 사용
        image_dir = config.IMG_DIR
        os.makedirs(image_dir, exist_ok=True)
    
    filepath = os.path.join(image_dir, filename)
    
    return image_dir, filepath

def get_folder_size(folder_path):
    """
    폴더 전체 용량 계산 (바이트)
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(filepath)
                except (OSError, IOError):
                    pass
    except (OSError, IOError):
        pass
    return total_size

def get_disk_usage():
    """
    디스크 사용량 확인 (바이트)
    Returns: (total, used, free)
    """
    try:
        stat = shutil.disk_usage(config.BASE_DIR)
        return stat.total, stat.used, stat.free
    except Exception as e:
        app_logger.error(f"[Logger] 디스크 사용량 확인 실패: {e}")
        return 0, 0, 0

def cleanup_old_files():
    """
    용량 관리: logs와 images 폴더의 오래된 파일 삭제
    - logs + images 합산이 STORAGE_LIMIT_GB 초과 시 오래된 파일부터 삭제
    - 또는 여유공간이 DISK_MIN_FREE_GB 미만일 때도 삭제
    """
    try:
        # 1. 현재 디스크 사용량 확인
        total, used, free = get_disk_usage()
        free_gb = free / (1024**3)
        
        # 2. logs + images 용량 계산
        logs_size = get_folder_size(config.LOG_DIR) if os.path.exists(config.LOG_DIR) else 0
        images_size = get_folder_size(config.IMG_DIR) if os.path.exists(config.IMG_DIR) else 0
        storage_total_gb = (logs_size + images_size) / (1024**3)
        
        app_logger.debug(f"[Logger] 💾 디스크 상태: 여유={free_gb:.2f}GB, logs+images={storage_total_gb:.2f}GB")
        
        # 3. 삭제 필요 여부 확인
        need_cleanup = False
        cleanup_reason = ""
        
        if free_gb < config.DISK_MIN_FREE_GB:
            need_cleanup = True
            cleanup_reason = f"여유공간 부족 ({free_gb:.2f}GB < {config.DISK_MIN_FREE_GB}GB)"
        elif storage_total_gb > config.STORAGE_LIMIT_GB:
            need_cleanup = True
            cleanup_reason = f"저장소 용량 초과 ({storage_total_gb:.2f}GB > {config.STORAGE_LIMIT_GB}GB)"
        
        if not need_cleanup:
            return
        
        app_logger.warning(f"[Logger] 🗑️ 용량 관리 시작: {cleanup_reason}")
        
        # 4. 삭제 대상 파일 수집 (날짜순 정렬)
        files_to_delete = []
        
        # logs 폴더의 모든 CSV 파일
        if os.path.exists(config.LOG_DIR):
            for root, dirs, files in os.walk(config.LOG_DIR):
                for file in files:
                    if file.endswith('.csv'):
                        filepath = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(filepath)
                            files_to_delete.append((mtime, filepath, 'log'))
                        except (OSError, IOError):
                            pass
        
        # images 폴더의 모든 이미지 파일
        if os.path.exists(config.IMG_DIR):
            for root, dirs, files in os.walk(config.IMG_DIR):
                for file in files:
                    if file.endswith(('.jpg', '.jpeg', '.png')):
                        filepath = os.path.join(root, file)
                        try:
                            mtime = os.path.getmtime(filepath)
                            files_to_delete.append((mtime, filepath, 'image'))
                        except (OSError, IOError):
                            pass
        
        # 5. 오래된 파일부터 정렬
        files_to_delete.sort(key=lambda x: x[0])  # mtime 기준 정렬
        
        # 6. 삭제 실행 (목표 달성까지)
        deleted_count = 0
        deleted_size = 0
        
        for mtime, filepath, file_type in files_to_delete:
            # 목표 달성 확인
            total, used, free = get_disk_usage()
            free_gb = free / (1024**3)
            logs_size = get_folder_size(config.LOG_DIR) if os.path.exists(config.LOG_DIR) else 0
            images_size = get_folder_size(config.IMG_DIR) if os.path.exists(config.IMG_DIR) else 0
            storage_total_gb = (logs_size + images_size) / (1024**3)
            
            # 목표 달성: 여유공간 확보 + 저장소 용량 제한 준수
            if free_gb >= config.DISK_MIN_FREE_GB and storage_total_gb <= config.STORAGE_LIMIT_GB:
                break
            
            # 파일 삭제
            try:
                file_size = os.path.getsize(filepath)
                os.remove(filepath)
                deleted_count += 1
                deleted_size += file_size
                app_logger.info(f"[Logger] 🗑️ 삭제: {os.path.basename(filepath)} ({file_size/(1024**2):.2f}MB)")
            except (OSError, IOError) as e:
                app_logger.error(f"[Logger] 파일 삭제 실패: {filepath}, {e}")
        
        if deleted_count > 0:
            app_logger.info(f"[Logger] ✅ 용량 관리 완료: {deleted_count}개 파일 삭제, {deleted_size/(1024**2):.2f}MB 해제")
            app_logger.info(f"[Logger] 💾 현재 상태: 여유={free_gb:.2f}GB, logs+images={storage_total_gb:.2f}GB")
        
        # 7. 빈 월별 폴더 정리
        # logs 폴더의 빈 월별 폴더 정리
        if os.path.exists(config.LOG_DIR):
            for month_dir in os.listdir(config.LOG_DIR):
                month_path = os.path.join(config.LOG_DIR, month_dir)
                if os.path.isdir(month_path):
                    try:
                        if not os.listdir(month_path):  # 빈 폴더
                            os.rmdir(month_path)
                            app_logger.debug(f"[Logger] 빈 폴더 삭제: {month_dir}")
                    except (OSError, IOError):
                        pass
        
        # images 폴더의 빈 월별 폴더 정리
        if os.path.exists(config.IMG_DIR):
            for month_dir in os.listdir(config.IMG_DIR):
                month_path = os.path.join(config.IMG_DIR, month_dir)
                if os.path.isdir(month_path):
                    try:
                        if not os.listdir(month_path):  # 빈 폴더
                            os.rmdir(month_path)
                            app_logger.debug(f"[Logger] 빈 이미지 폴더 삭제: {month_dir}")
                    except (OSError, IOError):
                        pass
                        
    except Exception as e:
        app_logger.error(f"[Logger] 용량 관리 오류: {e}")

def logger_thread_func(data_queue, stop_event):
    try:
        if not os.path.exists(config.LOG_DIR):
            os.makedirs(config.LOG_DIR, exist_ok=True)
    except OSError as e:
        print(f"[Logger Error] 로그 폴더 생성 실패: {e}")
        return
        
    print("[Logger] Service Started.")
    app_logger.info("[Logger] 로거 스레드 시작됨")
    
    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 10
    
    # 용량 관리 주기 (1시간마다 체크)
    last_cleanup_time = time.time()
    CLEANUP_INTERVAL = 3600  # 1시간
    
    while not stop_event.is_set():
        try:
            # 주기적 용량 관리
            if time.time() - last_cleanup_time > CLEANUP_INTERVAL:
                cleanup_old_files()
                last_cleanup_time = time.time()
            
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
            
            # 월별 폴더 구조로 경로 생성
            log_dir, filename = get_log_path()
            file_exists = os.path.isfile(filename)
            
            # 파일 쓰기 (에러 처리 강화)
            try:
                with open(filename, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # 헤더가 없으면 생성
                    if not file_exists:
                        # 모든 필드 포함: 센서값, 구동계, 계산값, 통계
                        writer.writerow([
                            'Timestamp',
                            # 센서값
                            'Temp_C', 'Hum_Pct', 'Soil_Raw', 'Soil_Pct', 'Lux',
                            # 계산값
                            'VPD_kPa', 'DLI_mol',
                            # 구동계 상태 (ON/OFF)
                            'Valve_Status', 'Fan_Status', 'LED_W_Status', 'LED_P_Status', 'Curtain_Status',
                            # 구동계 값 (속도/밝기 %)
                            'Fan_Speed_Pct', 'LED_W_Brightness_Pct', 'LED_P_Brightness_Pct',
                            # 비상 정지
                            'Emergency_Stop',
                            # 일일 통계
                            'Watering_Count_Today', 'Water_Used_Today_L',
                            # 추가 정보
                            'Note'
                        ])
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
