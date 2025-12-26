import serial
import time

# 아두이노가 연결된 포트 확인 (보통 /dev/ttyUSB0 또는 /dev/ttyACM0)
try:
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
except:
    ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)

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