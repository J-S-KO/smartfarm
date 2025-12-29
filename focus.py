import os
import time
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, HTTPServer

# 설정
PORT = 8000
IMG_FILE = "focus_frame.jpg"

class CameraThread(threading.Thread):
    def run(self):
        print("📷 카메라 스트리밍 시작 (1초 간격 갱신)...")
        while True:
            # 1초마다 사진을 덮어쓰기 (워밍업 없이 빠르게 촬영)
            cmd = [
                "rpicam-still",
                "-o", IMG_FILE,
                "--width", "640",   # 미리보기용이라 작게
                "--height", "480",
                "-t", "100",        # 바로 찍음
                "--nopreview"
            ]
            subprocess.run(cmd, stderr=subprocess.DEVNULL)
            time.sleep(0.5) # 0.5초 대기

def run_server():
    # 간단한 HTML 페이지 생성 (이미지를 계속 새로고침)
    index_html = f"""
    <html>
    <head>
        <title>Focus Check</title>
        <script>
            setInterval(function() {{
                var img = document.getElementById("cam");
                img.src = "{IMG_FILE}?t=" + new Date().getTime();
            }}, 1000); // 1초마다 이미지 새로고침
        </script>
        <style>
            body {{ text-align: center; background: #222; color: white; }}
            img {{ border: 2px solid red; margin-top: 20px; width: 640px; }}
        </style>
    </head>
    <body>
        <h2>Camera Focus Test</h2>
        <p>Rotate the lens to focus!</p>
        <img id="cam" src="{IMG_FILE}">
    </body>
    </html>
    """
    with open("index.html", "w") as f:
        f.write(index_html)

    # 웹 서버 시작
    server = HTTPServer(('0.0.0.0', PORT), SimpleHTTPRequestHandler)
    print(f"🌍 웹 서버 실행 중: http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    # 1. 카메라 쓰레드 시작
    cam_thread = CameraThread(daemon=True)
    cam_thread.start()

    # 2. 웹 서버 시작
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n종료합니다.")