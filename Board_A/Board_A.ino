#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

/* [15층 베란다 스마트팜 - Board A: Final Wiring]
 * - OLED: HW SPI (CS:10, DC:9, RES:8, MOSI:11, SCK:13)
 * - DHT11: Pin 4 (선정리 최적화)
 * - 조도센서: Pin A0
 * - 버튼: 5, 6, 7
 * - LED: 제거됨
 */

// 1. OLED 설정 (HW SPI 사용 - 속도 빠름)
// 13(SCK), 11(MOSI)는 하드웨어 고정
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8); 

// 2. 센서 설정
#define DHTPIN 4      // [변경] 기존 6 -> 4번으로 이동
DHT dht(DHTPIN, DHT11);

#define LIGHT_PIN A0  // [변경] 조도센서 A0 사용

// 3. 버튼 핀 설정 (3개: 5, 6, 7)
#define BTN_VPD 5  // [변경] 메인 버튼 (VPD 화면)
#define BTN_2   6  // 예비 버튼
#define BTN_3   7  // 예비 버튼

// 변수 설정
int lightRaw = 0;
float t = 0.0, h = 0.0;
float rcv_vpd = 0.0; // 수신된 VPD
float rcv_dli = 0.0; // 수신된 DLI

unsigned long lastSend = 0; // 센서 전송 타이머
const unsigned long INTERVAL_SEND = 2000; 

unsigned long lastDisp = 0; // 화면 갱신 타이머
const unsigned long INTERVAL_DISP = 100; 

void setup() {
  Serial.begin(9600);
  
  // 버튼 모드 설정 (풀업)
  pinMode(BTN_VPD, INPUT_PULLUP);
  pinMode(BTN_2, INPUT_PULLUP);
  pinMode(BTN_3, INPUT_PULLUP);

  u8g2.begin();
  dht.begin();
  // LED 관련 코드 삭제됨

  // 부팅 화면
  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(10, 30, "System Booting...");
    u8g2.drawStr(10, 45, "DHT:D4 / Light:A0");
  } while (u8g2.nextPage());
}

void loop() {
  // [1] 라즈베리파이 데이터 수신 (항상 체크)
  // 포맷: <VPD,DLI>
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '<') { 
      String data = Serial.readStringUntil('>'); 
      int commaIndex = data.indexOf(',');
      if (commaIndex != -1) {
        rcv_vpd = data.substring(0, commaIndex).toFloat();
        rcv_dli = data.substring(commaIndex + 1).toFloat();
      }
    }
  }

  unsigned long currentMillis = millis();

  // [2] 센서 읽기 및 데이터 전송 (2초 간격)
  if (currentMillis - lastSend > INTERVAL_SEND) {
    lastSend = currentMillis;
    t = dht.readTemperature();
    h = dht.readHumidity();
    lightRaw = analogRead(LIGHT_PIN); // A0에서 읽기

    // 라즈베리파이로 전송: t,h,light
    if (!isnan(t) && !isnan(h)) {
      Serial.print(t, 1); Serial.print(",");
      Serial.print((int)h); Serial.print(",");
      Serial.println(lightRaw);
    }
  }

  // [3] 화면 그리기 (0.1초 간격 - 버튼 반응 빠르게)
  if (currentMillis - lastDisp > INTERVAL_DISP) {
    lastDisp = currentMillis;
    
    // 버튼 상태 확인 (LOW가 눌린 상태) - 5번 핀
    bool isVpdPage = (digitalRead(BTN_VPD) == LOW);

    u8g2.firstPage();
    do {
      u8g2.setFont(u8g2_font_6x10_tf);

      if (isVpdPage) {
        // === [페이지 2] VPD 상세 화면 ===
        u8g2.drawStr(20, 10, "== VPD CHECK =="); 
        
        // 현재 값 표시
        u8g2.setCursor(0, 25); 
        u8g2.print("Now: "); u8g2.print(rcv_vpd, 2); u8g2.print(" kPa");

        // 상태 별점 로직
        u8g2.setCursor(0, 40); u8g2.print("Sts: ");
        if(rcv_vpd >= 0.8 && rcv_vpd <= 1.2)      u8g2.print("***** Good");
        else if(rcv_vpd >= 0.5 && rcv_vpd <= 1.5) u8g2.print("**--- SoSo");
        else                                      u8g2.print("*---- Bad!");

        // 참고 범위
        u8g2.drawStr(0, 58, "Ref: 0.8 ~ 1.2 kPa");

      } else {
        // === [페이지 1] 기본 대시보드 ===
        u8g2.drawStr(0, 10, "[Sensor]");
        u8g2.setCursor(55, 10); 
        u8g2.print("T:"); u8g2.print(t, 1);
        u8g2.print("  H:"); u8g2.print(h, 0); 

        // 중간: 조도
        u8g2.setCursor(0, 25); u8g2.print("Light: "); u8g2.print(lightRaw);
        u8g2.drawHLine(0, 32, 128); // 구분선

        // 하단: 파이 데이터
        u8g2.drawStr(0, 45, "[PiComputed]");
        u8g2.setCursor(0, 58); 
        u8g2.print("VPD:"); u8g2.print(rcv_vpd, 2);
        u8g2.print("  DLI:"); u8g2.print(rcv_dli, 2); 
      }
    } while (u8g2.nextPage());
  }
}
