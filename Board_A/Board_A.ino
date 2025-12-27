#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

/* --- 사용자 설정 변수 --- */
const int PIN_DHT = 2;
const int PIN_BTN_RAW = 5;
const int PIN_BTN_MENU = 6;
const int PIN_BTN_OK = 7;
const int SOIL_DRY = 520;  // 토양 센서 건조 시 값
const int SOIL_WET = 350;  // 토양 센서 침수 시 값
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
  Serial.println("=== BOARD A BOOT START ===");
  dht.begin();
  u8g2.begin();
  pinMode(PIN_BTN_RAW, INPUT_PULLUP);
  pinMode(PIN_BTN_MENU, INPUT_PULLUP);
  pinMode(PIN_BTN_OK, INPUT_PULLUP);
  Serial.println("=== SETUP FINISHED ===");
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
      // String 더하기(+) 금지 -> 나눠서 print 하기
      u8g2.setCursor(0, 10); 
      u8g2.print("T:"); u8g2.print(t, 1); u8g2.print("C H:"); u8g2.print((int)h); u8g2.print("%");
      
      u8g2.setCursor(0, 23); 
      u8g2.print("Soil:  "); u8g2.print(getGauge(soilPct, 60, 30));
      
      u8g2.setCursor(0, 36); 
      u8g2.print("Light: "); u8g2.print(getGauge(luxRaw, 500, 300)); // luxRaw 확인!
      
      u8g2.setCursor(0, 49); 
      u8g2.print("VPD:   "); u8g2.print(getGauge(vpd, 1.0, 0.6));
      
      u8g2.setCursor(0, 62); 
      u8g2.print(vpd > 1.5 ? "WARN: DRY!" : (soilPct < 30 ? "WARN: WATER!" : "HEALTHY"));
    } 
    // ... (RAW나 MENU 모드도 동일하게 + 연산자 대신 나눠서 print 하세요)
    
  } while (u8g2.nextPage());
  
  /* --- [추가] 라즈베리 파이로 센서 데이터 전송 (2초 간격) --- */
  static unsigned long lastDataSend = 0;
  if (millis() - lastDataSend > 2000) { 
    lastDataSend = millis();
    // 포맷: DATA,온도,습도,토양RAW,토양%,조도,VPD
    Serial.print("DATA,");
    Serial.print(t); Serial.print(",");
    Serial.print(h); Serial.print(",");
    Serial.print(soilRaw); Serial.print(",");
    Serial.print(soilPct); Serial.print(",");
    Serial.print(luxRaw); Serial.print(",");
    Serial.println(vpd);
  }

}