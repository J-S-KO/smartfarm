#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>
#include <Adafruit_NeoPixel.h>

/* [15층 베란다 스마트팜 - Board A: Bidirectional Communication]
 * 역할: 센서값 전송(TX) + 라즈베리파이 계산값 수신/표시(RX)
 * 업데이트: 라즈베리파이에서 Remote Upload 
 */

// 1. OLED 설정
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8); 

// 2. 센서 및 LED 설정
#define DHTPIN 6
DHT dht(DHTPIN, DHT11);

#define LED_PIN 7      
#define LED_COUNT 60   
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRBW + NEO_KHZ800);

int lightRaw = 0;
float t = 0.0, h = 0.0;
float rcv_vpd = 0.0; // 라즈베리파이에서 받은 VPD
float rcv_dli = 0.0; // 라즈베리파이에서 받은 DLI

unsigned long lastSend = 0;
const unsigned long INTERVAL_SEND = 2000; 

void setup() {
  Serial.begin(9600);
  u8g2.begin();
  dht.begin();
  strip.begin();
  strip.setBrightness(10); 
  strip.show(); 

  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(10, 30, "System Booting...");
  } while (u8g2.nextPage());
}

void loop() {
  // [중요] 라즈베리파이 데이터 수신 (항상 체크)
  // 데이터 포맷: <VPD,DLI> 예: <1.25,5.4>
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '<') { // 시작 문자 발견
      String data = Serial.readStringUntil('>'); // 끝 문자까지 읽기
      
      // 콤마(,) 위치 찾아서 파싱
      int commaIndex = data.indexOf(',');
      if (commaIndex != -1) {
        String vpdStr = data.substring(0, commaIndex);
        String dliStr = data.substring(commaIndex + 1);
        
        rcv_vpd = vpdStr.toFloat();
        rcv_dli = dliStr.toFloat();
      }
    }
  }

  // 2초마다 센서 읽기 및 화면 갱신
  if (millis() - lastSend > INTERVAL_SEND) {
    lastSend = millis();

    t = dht.readTemperature();
    h = dht.readHumidity();
    lightRaw = analogRead(A0);

    // 화면 그리기
    u8g2.firstPage();
    do {
      u8g2.setFont(u8g2_font_6x10_tf);
      
      // 상단: 센서값 (내가 읽은 것)
      u8g2.drawStr(0, 10, "[ Sensor ]");
      u8g2.setCursor(60, 10); u8g2.print("T:"); u8g2.print(t, 1);
      u8g2.setCursor(95, 10); u8g2.print("H:"); u8g2.print(h, 0);

      // 중간: 조도
      u8g2.setCursor(0, 25); u8g2.print("Light Raw: "); u8g2.print(lightRaw);

      u8g2.drawHLine(0, 32, 128); // 구분선

      // 하단: 라즈베리파이 계산값 (받은 것)
      u8g2.drawStr(0, 45, "[ Pi Computed ]");
      u8g2.setCursor(0, 58); 
      u8g2.print("VPD:"); u8g2.print(rcv_vpd, 2);
      u8g2.print(" DLI:"); u8g2.print(rcv_dli, 3);

    } while (u8g2.nextPage());

    // 라즈베리파이로 센서값 전송
    if (!isnan(t) && !isnan(h)) {
      Serial.print(t, 1); Serial.print(",");
      Serial.print((int)h); Serial.print(",");
      Serial.println(lightRaw);
    }
  }
}
