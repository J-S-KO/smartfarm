import serial
import time
import os

# 설정 변수
PORT_A = '/dev/ttyACM0'
PORT_B = '/dev/ttyACM1'
BAUD = 9600

def run_bridge():
    try:
        ser_a = serial.Serial(PORT_A, BAUD, timeout=1)
        ser_b = serial.Serial(PORT_B, BAUD, timeout=1)
        print(f"Connected: A on {PORT_A}, B on {PORT_B}")
    except Exception as e:
        print(f"Serial Connection Failed: {e}")
        return

    try:
        while True:
            if ser_a.in_waiting > 0:
                # 보드 A로부터 데이터 수신
                raw_data = ser_a.readline().decode('utf-8', errors='ignore').strip()
                if not raw_data: continue
                
                print(f"[RECV A] {raw_data}")

                if raw_data == "SYS_OFF":
                    print("Shutdown initiated by Board A.")
                    os.system("sudo shutdown -h now")
                    break
                
                elif raw_data.startswith("CMD_"):
                    # 보드 B로 명령 전달 (M0~M5)
                    cmd_to_b = raw_data.split("_")[1]
                    ser_b.write((cmd_to_b + "\n").encode())
                    print(f"[RELAY B] Sent: {cmd_to_b}")

            time.sleep(0.01) # CPU 점유율 방지
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        ser_a.close()
        ser_b.close()

if __name__ == "__main__":
    run_bridge()