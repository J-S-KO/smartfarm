import serial
import time
import os

# GitHub 설정 기반 포트 지정
try:
    ser_a = serial.Serial('/dev/ttyACM0', 9600, timeout=1) # Board_A (UI)
    ser_b = serial.Serial('/dev/ttyACM1', 9600, timeout=1) # Board_B (Neulsom)
except:
    print("Check Serial Port Connection!")

def main():
    print("SmartFarm Hub Started...")
    while True:
        if ser_a.in_waiting > 0:
            line = ser_a.readline().decode('utf-8').strip()
            
            # 1. 시스템 종료 명령 처리
            if line == "SYS_OFF":
                print("Command Received: Shutting down Raspberry Pi...")
                time.sleep(1)
                os.system("sudo shutdown -h now")
            
            # 2. 보드 B로 명령 중계 (M0, M1, M2...)
            elif line.startswith("CMD_"):
                cmd_to_b = line.split("_")[1] # "M0", "M4" 등 추출
                ser_b.write((cmd_to_b + "\n").encode())
                print(f"Relayed to Board_B: {cmd_to_b}")
                
        time.sleep(0.01)

if __name__ == "__main__":
    main()