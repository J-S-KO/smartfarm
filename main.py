import serial
import time
import math
import datetime
import os

# [설정]
PORT = '/dev/ttyACM0'
BAUDRATE = 9600
LOG_DIR = '/home/pi/smartfarm/logs'

# [설정] 변수 초기화
dli_daily_acc = 0.0
last_day = datetime.datetime.now().day
last_saved_minute = -1  # 1분 간격 저장을 위한 변수

# 로그 폴더 생성
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

def calculate_vpd(temp, humi):
    if temp is None or humi is None: return 0.0
    es = 0.6108 * math.exp((17.27 * temp) / (temp + 237.3))
    ea = es * (humi / 100.0)
    return round(es - ea, 2)

def calculate_dli(lux):
    ppfd = lux / 54.0
    return (ppfd * 2.0) / 1000000.0

def save_to_csv(timestamp, temp, humi, lux, vpd, dli):
    # 파일명 변경: smartfarm-YYYY-MM-DD.csv
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"{LOG_DIR}/smartfarm-{date_str}.csv"
    
    file_exists = os.path.isfile(filename)
    
    try:
        with open(filename, "a") as f:
            if not file_exists:
                f.write("Time,Temperature,Humidity,Lux,VPD,DLI_Accumulated\n")
            
            # 초 단위까지 기록
            f.write(f"{timestamp},{temp},{humi},{int(lux)},{vpd},{dli:.4f}\n")
    except Exception as e:
        print(f"파일 저장 실패: {e}")

# --- 메인 실행부 ---
try:
    print(f"시스템 시작... 로그 위치: {LOG_DIR}")
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    time.sleep(2)
    ser.reset_input_buffer()
    print("센서 데이터 수신 및 DLI 계산 중 (저장은 1분마다)")

    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').rstrip()
                data = line.split(',')
                
                if len(data) == 3:
                    temp = float(data[0])
                    humi = int(data[1])
                    lux_raw = int(data[2])
                    
                    lux = (lux_raw / 1023.0) * 10000
                    vpd = calculate_vpd(temp, humi)
                    
                    now = datetime.datetime.now()
                    
                    # 날짜 바뀌면 DLI 리셋
                    if now.day != last_day:
                        dli_daily_acc = 0.0
                        last_day = now.day
                    
                    # DLI는 '매 순간' 계산해야 정확함 (누적)
                    dli_daily_acc += calculate_dli(lux)

                    # 아두이노 화면 업데이트 (실시간)
                    send_message = f"<{vpd},{dli_daily_acc:.3f}>"
                    ser.write(send_message.encode())

                    # --- [핵심 변경] 저장 로직 (1분에 한 번만) ---
                    # 현재 분(Minute)이 마지막 저장한 분과 다를 때만 저장
                    if now.minute != last_saved_minute:
                        ts = now.strftime("%Y-%m-%d %H:%M:%S")
                        print(f"[{ts}] 1분 로그 저장: {temp}C, {humi}%, VPD {vpd}")
                        save_to_csv(ts, temp, humi, lux, vpd, dli_daily_acc)
                        last_saved_minute = now.minute

            except ValueError:
                pass
            except Exception as e:
                print(f"에러: {e}")
                
except KeyboardInterrupt:
    print("\n시스템 종료")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
