#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

/* --- 사용자 설정 변수 --- */
const int PIN_DHT = 2;
const int PIN_BTN_RAW = 5;
const int PIN_BTN_MENU = 6;
const int PIN_BTN_OK = 7;
const int SOIL_DRY = 530;  // 토양 센서 건조 시 값
const int SOIL_WET = 300;  // 토양 센서 침수 시 값
const int HOME_TIMEOUT = 7000; // 홈 화면 복귀 시간 (ms)

/* --- 장치 초기화 --- */
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8);
DHT dht(PIN_DHT, DHT11);

/* --- 상태 관리 --- */
enum State { HOME, RAW, MENU } currState = HOME;
unsigned long lastAction = 0;
int menuIdx = 0;
const int MENU_CNT = 7;
const char* menus[] = {
  "LED(White) On/Off", "Water Valve On/Off", "LED(White) Test",
  "LED(Purple) Test",  "FAN PWM Test",      "Step Motor Test", "System Off"
};

/* --- 게이지 바 헬퍼 --- */
String getGauge(float val, float opt, float range) {
  int pos = map(constrain(val * 10, (opt - range) * 10, (opt + range) * 10), (opt - range) * 10, (opt + range) * 10, 0, 8);
  String g = "---------"; g.setCharAt(pos, '*');
  return g;
}

void setup() {
  Serial.begin(9600);
  dht.begin();
  u8g2.begin();
  pinMode(PIN_BTN_RAW, INPUT_PULLUP);
  pinMode(PIN_BTN_MENU, INPUT_PULLUP);
  pinMode(PIN_BTN_OK, INPUT_PULLUP);
}

void loop() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  int soilRaw = analogRead(A1);
  int luxRaw = analogRead(A0);
  int soilPct = map(constrain(soilRaw, SOIL_WET, SOIL_DRY), SOIL_DRY, SOIL_WET, 0, 100);
  
  float vpd = 0;
  if (!isnan(t) && !isnan(h)) {
    // VPD 공식: $es = 0.61078 \times \exp((17.27 \times t) / (t + 237.3))$, $VPD = es \times (1 - h/100)$
    float es = 0.61078 * exp((17.27 * t) / (t + 237.3));
    vpd = es * (1.0 - (h / 100.0));
  }

  // 버튼 제어 로직
  if (digitalRead(PIN_BTN_RAW) == LOW) { currState = RAW; lastAction = millis(); delay(200); }
  if (digitalRead(PIN_BTN_MENU) == LOW) {
    if (currState != MENU) { currState = MENU; menuIdx = 0; }
    else menuIdx = (menuIdx + 1) % MENU_CNT;
    lastAction = millis(); delay(200);
  }
  if (digitalRead(PIN_BTN_OK) == LOW && currState == MENU) {
    if (menuIdx == 6) Serial.println(F("SYS_OFF"));
    else Serial.print(F("CMD_M")), Serial.println(menuIdx);
    lastAction = millis(); delay(500);
  }

  if (millis() - lastAction > HOME_TIMEOUT) currState = HOME;

  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_6x10_tf);
    if (currState == HOME) {
      u8g2.setCursor(0, 10); u8g2.print("T:" + String(t, 1) + "C H:" + String((int)h) + "%");
      u8g2.setCursor(0, 23); u8g2.print("Soil:  " + getGauge(soilPct, 60, 30));
      u8g2.setCursor(0, 36); u8g2.print("Light: " + getGauge(luxRaw, 500, 300));
      u8g2.setCursor(0, 49); u8g2.print("VPD:   " + getGauge(vpd, 1.0, 0.6));
      u8g2.setCursor(0, 62); u8g2.print(vpd > 1.5 ? "WARN: DRY!" : (soilPct < 30 ? "WARN: WATER!" : "HEALTHY"));
    } else if (currState == RAW) {
      u8g2.drawStr(0, 10, "[ RAW DATA ]");
      u8g2.setCursor(0, 25); u8g2.print("T/H: " + String(t) + "/" + String(h));
      u8g2.setCursor(0, 38); u8g2.print("Soil: " + String(soilRaw) + " (" + String(soilPct) + "%)");
      u8g2.setCursor(0, 51); u8g2.print("Lux: " + String(luxRaw));
    } else if (currState == MENU) {
      u8g2.drawStr(0, 10, "[ SMART MENU ]");
      for (int i = 0; i < 4; i++) {
        int idx = (menuIdx / 4 * 4) + i;
        if (idx >= MENU_CNT) break;
        if (idx == menuIdx) { u8g2.drawBox(0, 14+(i*12), 128, 12); u8g2.setDrawColor(0); }
        else u8g2.setDrawColor(1);
        u8g2.setCursor(4, 24+(i*12)); u8g2.print(menus[idx]);
      }
      u8g2.setDrawColor(1);
    }
  } while (u8g2.nextPage());
}