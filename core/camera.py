import threading
import time
import os
import subprocess
from datetime import datetime
import config as cfg
from .logger import app_logger, get_image_path

class CameraThread(threading.Thread):
    def __init__(self, sys_state=None, state_lock=None, ser_b=None, ser_b_lock=None):
        threading.Thread.__init__(self)
        self.running = True
        
        # 설정 로드
        self.interval = cfg.CAM_INTERVAL_MIN * 60  # 분을 초로 변환
        
        # 상태 변수
        self.force_capture = False  # 수동 촬영 플래그
        self.last_auto_time = time.time() # 시작하자마자 자동 촬영 되는 것 방지
        self.sys_state = sys_state  # 시스템 상태 (조도 확인용)
        self.state_lock = state_lock  # 상태 락
        self.ser_b = ser_b  # 시리얼 포트 (LED 제어용)
        self.ser_b_lock = ser_b_lock  # 시리얼 락
        
        # 기본 이미지 폴더 생성 (월별 폴더는 get_image_path에서 자동 생성)
        if not os.path.exists(cfg.IMG_DIR):
            os.makedirs(cfg.IMG_DIR)
            app_logger.info(f"[Cam] 기본 이미지 폴더 생성: {cfg.IMG_DIR}")

    def trigger_manual_capture(self):
        """ 메인 스레드에서 수동 촬영 요청 시 호출 """
        self.force_capture = True
        app_logger.info("[Cam] 수동 촬영 플래그 설정됨 (대기중...)")

    def capture_image(self, tag="Auto"):
        """ 실제 사진을 찍는 함수 (tag: Auto 또는 User) """
        # 자동 촬영인 경우 조도 확인 (100 lux 이하이면 촬영하지 않음)
        if tag == "Auto":
            if self.sys_state and self.state_lock:
                with self.state_lock:
                    current_lux = self.sys_state.get('lux', 0)
                if current_lux <= 100:
                    app_logger.info(f"[Cam] ⚠️ 조도가 낮아 자동 촬영 건너뜀 (조도: {current_lux} Lux <= 100 Lux)")
                    return
            else:
                app_logger.warning("[Cam] ⚠️ sys_state가 설정되지 않아 조도 확인 불가, 촬영 진행")
        
        # 수동 촬영은 LED 자동 제어 없이 단순히 촬영만 수행 (LED는 사용자가 직접 제어)
        
        try:
            # 파일명 생성: YYYY-MM-DD_HH-MM-SS_Tag.jpg
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{timestamp}_{tag}.jpg"
            # 태그에 따라 폴더 경로 생성 (Auto: 월별 폴더, User: manual 폴더)
            image_dir, filepath = get_image_path(filename, tag)
            
            # 명령어 실행 (libcamera-still / rpicam-still)
            # -t 1 : 1ms 대기 후 촬영 (즉시 촬영)
            # -o : 출력 파일 경로
            cmd = ["rpicam-still", "-t", "1", "-o", filepath, "--width", "1920", "--height", "1080"]
            
            app_logger.info(f"[Cam] 📸 촬영 시도... ({tag}) -> {filename}")
            app_logger.info(f"[Cam] 📁 저장 경로: {filepath}")
            
            # 서브프로세스로 실행 (메인 스레드 멈춤 방지)
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                app_logger.info(f"[Cam] ✅ 저장 성공: {filepath}")
            else:
                app_logger.error(f"[Cam] ❌ 촬영 실패 (Code {result.returncode}): {result.stderr.decode('utf-8')}")

        except Exception as e:
            app_logger.error(f"[Cam] 촬영 중 예외 발생: {e}")

    def run(self):
        app_logger.info("[Cam] 카메라 서비스 시작 (수동: CMD_M6 / 자동: 00, 30분)")
        
        while self.running:
            try:
                # 1. 수동 촬영 확인 (우선 순위 높음)
                if self.force_capture:
                    self.capture_image("User")
                    self.force_capture = False  # 플래그 초기화
                    time.sleep(1) # 연속 촬영 방지 쿨타임

                # 2. 자동 촬영 로직 (정각 00분, 30분 체크)
                now = datetime.now()
                
                # 매시 0분 혹은 30분이고, 
                # 마지막 자동 촬영 후 60초 이상 지났을 때만 (중복 촬영 방지)
                if (now.minute == 0 or now.minute == 30):
                    if time.time() - self.last_auto_time > 60:
                        # 조도 확인 (100 lux 이하이면 촬영하지 않음)
                        # sys_state는 외부에서 주입받아야 하므로, 
                        # 조도 확인은 capture_image 함수 내부에서 처리
                        app_logger.info("[Cam] ⏰ 정기 촬영 시간 도달")
                        self.capture_image("Auto")
                        self.last_auto_time = time.time()

                time.sleep(0.5)  # CPU 점유율 방지

            except Exception as e:
                app_logger.error(f"[Cam] 스레드 루프 에러: {e}")
                time.sleep(1)

    def stop(self):
        self.running = False
        self.join()