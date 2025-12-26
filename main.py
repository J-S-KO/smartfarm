import serial
import time
import threading

# 확인된 포트 설정
PORT_A = '/dev/ttyACM0'  # Board_A (Uno)
PORT_B = '/dev/ttyACM1'  # Board_B (Neulsom)

ser_a = serial.Serial(PORT_A, 9600, timeout=1)
ser_b = serial.Serial(PORT_B, 9600, timeout=1)

def listen_board_a():
    while True:
        if ser_a.in_waiting > 0:
            line = ser_a.readline().decode('utf-8').strip()
            
            # 버튼 명령 처리
            if line == "B1":
                ser_b.write(b'1')
                update_oled("TR Control!")
            elif line == "B2":
                ser_b.write(b'2')
                update_oled("Relay Control!")
            elif line == "B3":
                ser_b.write(b'3')
                update_oled("LED & Motor!")
            
            # 센서 데이터 수신 시 처리 로직 (필요시 추가)
            elif line.startswith("D:"):
                pass 

def update_oled(msg):
    # Board_A의 OLED로 짧은 상태 메시지 전송
    ser_a.write((msg + "\n").encode())

# 수신 스레드 가동
threading.Thread(target=listen_board_a, daemon=True).start()

print("시스템 가동 시작... (Ctrl+C로 종료)")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n시스템을 종료합니다.")
    ser_a.close()
    ser_b.close()