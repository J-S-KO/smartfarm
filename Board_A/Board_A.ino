#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>
#include <Adafruit_NeoPixel.h>

/* [15층 베란다 스마트팜 - Board A: Final Version]
 * 기능: 센서(DHT11) 송신 + 파이 데이터 수신 + OLED(U8g2) UI + 버튼 제어
 */

// 1. OLED 설정 (SPI)
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8); 

// 2. 센서 및 LED 설정
#define DHTPIN 6
DHT dht(DHTPIN, DHT11);

#define LED_PIN 7      
#define LED_COUNT 60   
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRBW + NEO_KHZ800);

// 3. 버튼 핀 설정 (2,3,4,5)
#define BTN_VPD 2  // VPD 상세 확인
#define BTN_3   3
#define BTN_4   4
#define BTN_5   5

// 변수 설정
int lightRaw = 0;
float t = 0.0, h = 0.0;
float rcv_vpd = 0.0; // 수신된 VPD
float rcv_dli = 0.0; // 수신된 DLI

unsigned long lastSend = 0; // 센서 전송 타이머
const unsigned long INTERVAL_SEND = 2000; 

unsigned long lastDisp = 0; // 화면 갱신 타이머 (반응속도 향상)
const unsigned long INTERVAL_DISP = 100; 

void setup() {
  Serial.begin(9600);
  
  // 핀 모드 설정 (풀업 저항 사용)
  pinMode(BTN_VPD, INPUT_PULLUP);
  pinMode(BTN_3, INPUT_PULLUP);
  pinMode(BTN_4, INPUT_PULLUP);
  pinMode(BTN_5, INPUT_PULLUP);

  u8g2.begin();
  dht.begin();
  strip.begin();
  strip.setBrightness(10); 
  strip.show(); 

  // 부팅 화면
  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(10, 30, "System Booting...");
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
    lightRaw = analogRead(A0);

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
    
    // 버튼 상태 확인 (LOW가 눌린 상태)
    bool isVpdPage = (digitalRead(BTN_VPD) == LOW);

    u8g2.firstPage();
    do {
      u8g2.setFont(u8g2_font_6x10_tf);

      if (isVpdPage) {
        // === [페이지 2] VPD 상세 화면 ===
        u8g2.drawStr(20, 10, "== VPD CHECK =="); // 제목 중앙 정렬 느낌
        
        // 현재 값 표시
        u8g2.setCursor(0, 25); 
        u8g2.print("Now: "); u8g2.print(rcv_vpd, 2); u8g2.print(" kPa");

        // 상태 별점 로직 (0.8 ~ 1.2 최적)
        u8g2.setCursor(0, 40); u8g2.print("Sts: ");
        if(rcv_vpd >= 0.8 && rcv_vpd <= 1.2)      u8g2.print("***** Good");
        else if(rcv_vpd >= 0.5 && rcv_vpd <= 1.5) u8g2.print("**--- SoSo");
        else                                      u8g2.print("*---- Bad!");

        // 참고 범위
        u8g2.drawStr(0, 58, "Ref: 0.8 ~ 1.2 kPa");

      } else {
        // === [페이지 1] 기본 대시보드 ===
        
        // 상단: 센서 (공백 제거 및 정리)
        u8g2.drawStr(0, 10, "[Sensor]");
        u8g2.setCursor(55, 10); // 위치 조정으로 겹침 방지
        u8g2.print("T:"); u8g2.print(t, 1);
        u8g2.print("  H:"); u8g2.print(h, 0); // 공백 2칸 추가

        // 중간: 조도
        u8g2.setCursor(0, 25); u8g2.print("Light: "); u8g2.print(lightRaw);
        u8g2.drawHLine(0, 32, 128); // 구분선

        // 하단: 파이 데이터 (공백 제거)
        u8g2.drawStr(0, 45, "[PiComputed]");
        u8g2.setCursor(0, 58); 
        u8g2.print("VPD:"); u8g2.print(rcv_vpd, 2);
        u8g2.print("  DLI:"); u8g2.print(rcv_dli, 2); // DLI 소수점 2자리로 줄임
      }
    } while (u8g2.nextPage());
  }
}
