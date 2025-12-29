import serial
import time

# 아두이노가 연결된 포트 확인 (보통 /dev/ttyUSB0 또는 /dev/ttyACM0)
# 주의: 이 스크립트는 테스트용이며, 실제 프로젝트와 프로토콜이 다를 수 있습니다.
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
except:
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
    except Exception as e:
        print(f"시리얼 포트 연결 실패: {e}")
        exit(1)

print(f"Connected to: {ser.name}")
time.sleep(2) # 아두이노 리셋 대기

while True:
    # 테스트값: VPD=1.23, DLI=45.6
    msg = "<1.23,45.6>"
    ser.write(msg.encode())
    print(f"Sent: {msg}")
    
    # 아두이노 응답 확인
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').rstrip()
        print(f"Received: {line}")
        
    time.sleep(2)

