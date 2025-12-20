import serial
import time

# 아두이노 포트 설정 (본인 환경에 맞게 수정 필요!)
# 보통 '/dev/ttyACM0' 아니면 '/dev/ttyUSB0' 입니다.
PORT = '/dev/ttyACM0' 
BAUDRATE = 9600

try:
    # 아두이노와 연결 시도
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    ser.reset_input_buffer() # 기존에 쌓인 쓰레기 값 비우기
    
    print(f"아두이노와 연결되었습니다! ({PORT})")
    print("데이터를 기다리는 중... (아두이노 리셋 버튼을 누르면 바로 뜹니다)")
    print("-" * 30)

    while True:
        # 데이터가 들어오면
        if ser.in_waiting > 0:
            # 한 줄 읽어서, 불필요한 공백 제거하고, utf-8로 해석
            line = ser.readline().decode('utf-8').rstrip()
            
            # 화면에 출력
            print(f"[수신]: {line}")
            
except serial.SerialException:
    print(f"에러: {PORT} 포트를 찾을 수 없거나 연결할 수 없습니다.")
    print("USB가 잘 꽂혀있는지, 포트 이름이 맞는지 확인해주세요.")
except KeyboardInterrupt:
    print("\n통신 종료 (Ctrl+C)")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
