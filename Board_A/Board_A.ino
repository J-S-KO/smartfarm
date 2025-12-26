#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

// [OLED 설정] SPI 방식 SH1106
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8);

// [센서 및 버튼 핀]
#define DHTPIN 2     
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

#define PIN_CDS A0
#define PIN_SOIL A1

// 사용자 배선 반영: 버튼을 5, 6, 7번 핀으로 변경
const int BTN_1 = 5; // 기능 1: TR (팬/밸브)
const int BTN_2 = 6; // 기능 2: 릴레이 (펌프)
const int BTN_3 = 7; // 기능 3: 스텝모터 & MOSFET (LED)

String displayMsg = "System Ready"; 
float t = 0.0, h = 0.0;
int luxVal = 0, soilVal = 0;

void setup() {
  Serial.begin(9600);
  dht.begin();
  u8g2.begin();
  
  pinMode(BTN_1, INPUT_PULLUP);
  pinMode(BTN_2, INPUT_PULLUP);
  pinMode(BTN_3, INPUT_PULLUP);
}

void loop() {
  t = dht.readTemperature();
  h = dht.readHumidity();
  luxVal = analogRead(PIN_CDS);
  soilVal = analogRead(PIN_SOIL);

  // 데이터 전송
  if (!isnan(t) && !isnan(h)) {
    Serial.print("D:");
    Serial.print(t, 1); Serial.print(",");
    Serial.print((int)h); Serial.print(",");
    Serial.print(soilVal); Serial.print(",");
    Serial.println(luxVal);
  }

  // 버튼 처리 (물리적 순서에 맞게 B1, B2, B3 전송)
  if(digitalRead(BTN_1) == LOW) { Serial.println("B1"); delay(300); }
  if(digitalRead(BTN_2) == LOW) { Serial.println("B2"); delay(300); }
  if(digitalRead(BTN_3) == LOW) { Serial.println("B3"); delay(300); }

  if (Serial.available() > 0) {
    displayMsg = Serial.readStringUntil('\n');
  }

  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(0, 10, "[Smart Farm 3-Board]");
    u8g2.drawStr(0, 22, "--------------------");
    u8g2.setCursor(0, 35);
    u8g2.print("T:"); u8g2.print(t, 1); u8g2.print("C H:"); u8g2.print((int)h); u8g2.print("%");
    u8g2.setCursor(0, 48);
    u8g2.print("S:"); u8g2.print(soilVal); u8g2.print(" L:"); u8g2.print(luxVal);
    u8g2.setCursor(0, 62);
    u8g2.print("MSG: "); u8g2.print(displayMsg);
  } while (u8g2.nextPage());

  delay(100);
}