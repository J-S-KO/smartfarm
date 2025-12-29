import time
import os
import subprocess
import shutil
from datetime import datetime
import config  # 설정 파일 연동

# ==========================================
# 📸 카메라 명령어 자동 감지
# ==========================================
def get_camera_command():
    """
    OS 환경에 맞는 카메라 명령어를 찾습니다.
    Bookworm(최신): rpicam-still 또는 libcamera-still
    Legacy(구형): raspistill
    """
    if shutil.which("rpicam-still"):
        return "rpicam-still"
    elif shutil.which("libcamera-still"):
        return "libcamera-still"
    elif shutil.which("raspistill"):
        return "raspistill"
    else:
        return None

# 전역 변수로 명령어 설정
CAM_CMD = get_camera_command()

def camera_loop(stop_event):
    """
    [Main Thread용 함수]
    설정된 시간마다 자동으로 사진을 찍습니다.
    """
    if CAM_CMD is None:
        print("[Cam Error] ❌ 카메라 명령어를 찾을 수 없습니다. (rpicam-still/libcamera-still/raspistill)")
        return

    print(f"[Cam] 카메라 서비스 시작 (사용 명령어: {CAM_CMD})")
    
    # 1. 저장 폴더 안전 점검
    if not os.path.exists(config.IMG_DIR):
        os.makedirs(config.IMG_DIR)
        print(f"[Cam] 폴더 생성: {config.IMG_DIR}")

    last_shot_time = 0
    interval_sec = config.CAM_INTERVAL_MIN * 60  # 루프 밖에서 한 번만 계산

    while not stop_event.is_set():
        # 2. 촬영 조건 확인
        if config.USE_AUTO_CAM and (time.time() - last_shot_time > interval_sec):
            if take_picture("Auto"):  # 성공 시에만 시간 업데이트
                last_shot_time = time.time()
        
        time.sleep(5) 

def take_picture(trigger="Auto"):
    """
    실제 사진을 찍는 함수
    trigger: 파일명 태그
    """
    if CAM_CMD is None:
        print("[Cam Error] ❌ 카메라 명령어가 설치되지 않았습니다.")
        return None

    # 폴더는 camera_loop에서 이미 생성되므로 중복 체크 제거
    # 단독 실행 시를 대비해 안전 체크는 유지
    try:
        if not os.path.exists(config.IMG_DIR):
            os.makedirs(config.IMG_DIR, exist_ok=True)
    except OSError as e:
        print(f"[Cam Error] ❌ 이미지 저장 폴더 생성 실패: {e}")
        return None
    
    now = datetime.now()
    filename = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}_{trigger}.jpg"
    filepath = os.path.join(config.IMG_DIR, filename)
    
    # 명령어 구성
    cmd = [
        CAM_CMD,
        "-o", filepath,
        "--width", "1920",
        "--height", "1080",
        "--nopreview"
    ]

    # 구형 raspistill이 아닐 경우에만 -t 1 (즉시 촬영) 옵션 사용
    # rpicam-still은 튜닝 시간이 필요할 수 있으나 테스트를 위해 짧게 설정
    if "raspistill" not in CAM_CMD:
        cmd.extend(["-t", "1000"]) # 1초 대기 (너무 짧으면 노출/화이트밸런스 틀어짐)
    else:
        cmd.extend(["-t", "1000"]) # raspistill도 1초

    try:
        print(f"[Cam] 📸 촬영 시도... ({trigger}) -> {filepath}")
        
        # [핵심 수정] stderr=subprocess.PIPE 로 변경하여 에러 내용을 잡아냄
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[Cam] ✅ 저장 성공: {filename}")
            return filepath
        else:
            # 여기가 중요합니다. 실패하면 왜 실패했는지 토해냅니다.
            print(f"[Cam Error] ❌ 촬영 실패 (코드 {result.returncode})")
            print(f"   👉 이유: {result.stderr.strip()}") # 실제 에러 메시지 출력
            return None

    except Exception as e:
        print(f"[Cam Error] ❌ 실행 중 예외 발생: {e}")
        return None

# 단독 테스트용
if __name__ == "__main__":
    # config 가짜 객체 생성 (단독 실행 시 에러 방지)
    if not hasattr(config, 'IMG_DIR'):
        config.IMG_DIR = './photos'
    
    print("=== 카메라 모듈 단독 테스트 ===")
    take_picture("TestRun")