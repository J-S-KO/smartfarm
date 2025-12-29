#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

/* --- 핀 설정 --- */
const int PIN_DHT = 2;
const int PIN_BTN_RAW = 5;
const int PIN_BTN_MENU = 6;
const int PIN_BTN_OK = 7;

const int SOIL_DRY = 520;  
const int SOIL_WET = 350;  
const int HOME_TIMEOUT = 10000;

U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8);
DHT dht(PIN_DHT, DHT11);

enum State { HOME, RAW, MENU } currState = HOME;
unsigned long lastAction = 0;
int menuIdx = 0;

String vState="OFF", fState="OFF", wState="OFF", pState="OFF"; 
int sysHour=0, sysMin=0;    

long sumLux=0, sumSoil=0;
int sampleCount=0;
int dispLux=0, dispSoilRaw=0, dispSoilPct=0; 
unsigned long lastSensorUpdate=0;

float accumulatedDLI = 0.0;
unsigned long lastDLITime = 0;
bool dliResetDone = false;

const int MENU_CNT = 8;
const char* menus[] = {
  "LED(White) On/Off",
  "Water Valve On/Off",
  "LED(White) Test",
  "LED(Purple) Test",
  "FAN PWM Test",
  "Step Motor Test",
  "Camera Test",
  "System Off"
};

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);
  dht.begin();
  u8g2.begin();
  
  pinMode(PIN_BTN_RAW, INPUT_PULLUP);
  pinMode(PIN_BTN_MENU, INPUT_PULLUP);
  pinMode(PIN_BTN_OK, INPUT_PULLUP);
  
  lastDLITime = millis();
}

void drawBar(int x, int y, int w, int h, int val, int maxVal) {
  u8g2.drawFrame(x, y, w, h);
  int barW = map(constrain(val, 0, maxVal), 0, maxVal, 0, w - 2);
  if (barW > 0) u8g2.drawBox(x + 1, y + 1, barW, h - 2);
}

void drawCheckbox(int x, int y, String label, String state) {
  u8g2.drawFrame(x, y, 10, 10);
  if (state == "ON") u8g2.drawBox(x + 2, y + 2, 6, 6);
  u8g2.setCursor(x + 14, y + 8); u8g2.print(label);
}

// [NEW] 팝업 메시지를 띄우는 함수
void drawPopup(const char* msg) {
  u8g2.firstPage();
  do {
    // 배경을 살짝 지우거나 박스를 그림
    u8g2.setDrawColor(0);
    u8g2.drawBox(10, 20, 108, 24); // 글자 들어갈 공간 지우기
    u8g2.setDrawColor(1);
    u8g2.drawFrame(10, 20, 108, 24); // 테두리 그리기
    
    u8g2.setFont(u8g2_font_6x10_tf);
    // 글자 가운데 정렬 계산 (대략)
    int strW = u8g2.getStrWidth(msg);
    int startX = 64 - (strW / 2);
    u8g2.setCursor(startX, 36);
    u8g2.print(msg);
  } while (u8g2.nextPage());
}

void loop() {
  float t = dht.readTemperature();
  float h = dht.readHumidity();
  int rawS = analogRead(A1);
  int rawL = analogRead(A0);
  
  sumSoil += rawS; sumLux += rawL; sampleCount++;

  if (millis() - lastSensorUpdate > 1000) {
    if (sampleCount > 0) {
      dispSoilRaw = sumSoil / sampleCount; 
      dispLux = sumLux / sampleCount;      
      dispSoilPct = map(constrain(dispSoilRaw, SOIL_WET, SOIL_DRY), SOIL_DRY, SOIL_WET, 0, 100);
    }
    sumSoil = 0; sumLux = 0; sampleCount = 0;
    lastSensorUpdate = millis();
  }

  float vpd = 0.0;
  if (!isnan(t) && !isnan(h)) {
    float es = 0.61078 * exp((17.27 * t) / (t + 237.3));
    vpd = es * (1.0 - (h / 100.0));
  }

  if (Serial.available() > 0) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.startsWith("STATE,")) {
      int idx[6];
      int currentIdx = -1;
      for(int i=0; i<6; i++) {
        currentIdx = input.indexOf(',', currentIdx + 1);
        idx[i] = currentIdx;
      }
      if (idx[5] != -1) { 
        vState = input.substring(idx[0]+1, idx[1]);
        fState = input.substring(idx[1]+1, idx[2]);
        wState = input.substring(idx[2]+1, idx[3]);
        pState = input.substring(idx[3]+1, idx[4]);
        sysHour = input.substring(idx[4]+1, idx[5]).toInt();
        sysMin  = input.substring(idx[5]+1).toInt();
      }
    }
  }

  if (sysHour == 0 && sysMin == 0) {
    if (!dliResetDone) { accumulatedDLI = 0.0; dliResetDone = true; }
  } else { dliResetDone = false; }

  unsigned long now = millis();
  float dt = (now - lastDLITime) / 1000.0;
  if (dt >= 0.5) {
    lastDLITime = now;
    float ppfd = (rawL * 2.0) * 0.0185; 
    accumulatedDLI += (ppfd * dt) / 1000000.0;
  }

  if (digitalRead(PIN_BTN_RAW) == LOW) { currState = RAW; lastAction = millis(); delay(200); }
  if (digitalRead(PIN_BTN_MENU) == LOW) {
    if (currState != MENU) { currState = MENU; menuIdx = 0; }
    else menuIdx = (menuIdx + 1) % MENU_CNT;
    lastAction = millis(); delay(200);
  }
  
  // [업그레이드된 버튼 처리]
  if (digitalRead(PIN_BTN_OK) == LOW && currState == MENU) {
    // 1. 피드백 메시지 결정
    const char* msg = "Sending...";
    if (menuIdx == 6) msg = "Say Cheese!";    // 카메라 테스트 시
    else if (menuIdx == 7) msg = "Power OFF..."; // 종료 시
    else msg = "Processing...";               // 일반 제어 시

    // 2. 화면에 팝업 띄우기 (즉시)
    drawPopup(msg);

    // 3. 시리얼 명령 전송
    if (menuIdx == 7) Serial.println(F("SYS_OFF"));
    else { 
      Serial.print(F("CMD_M")); Serial.println(menuIdx); 
    }
    
    // 4. 사용자가 메시지를 볼 수 있게 1초 대기
    delay(1000); 
    
    lastAction = millis();
  }
  
  if (millis() - lastAction > HOME_TIMEOUT) currState = HOME;

  // --- 화면 그리기 (기존 코드 유지) ---
  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_helvB08_tr);
    u8g2.setCursor(0, 10);
    if(sysHour < 10) u8g2.print("0"); u8g2.print(sysHour); u8g2.print(":");
    if(sysMin < 10) u8g2.print("0"); u8g2.print(sysMin);
    
    u8g2.setCursor(55, 10);
    if(isnan(t)) { u8g2.print("SensErr"); }
    else {
      u8g2.print("T:"); u8g2.print((int)t); 
      u8g2.print(" H:"); u8g2.print((int)h); u8g2.print("%");
    }
    u8g2.drawHLine(0, 13, 128);

    if (currState == HOME) {
       u8g2.setFont(u8g2_font_open_iconic_thing_1x_t); u8g2.drawGlyph(0, 32, 72);
       u8g2.setFont(u8g2_font_6x10_tf);
       u8g2.setCursor(12, 24); u8g2.print("Soil: "); u8g2.print(dispSoilPct); u8g2.print("%");
       drawBar(12, 27, 110, 6, dispSoilPct, 100);

       u8g2.setFont(u8g2_font_open_iconic_weather_1x_t); u8g2.drawGlyph(0, 52, 69);
       u8g2.setFont(u8g2_font_6x10_tf);
       u8g2.setCursor(12, 44); u8g2.print("Lux: "); u8g2.print(dispLux);
       drawBar(12, 47, 110, 6, dispLux, 1000);

       u8g2.setCursor(0, 64);
       if (dispSoilPct < 30) u8g2.print("! WATER NEEDED !");
       else if (vpd > 1.5) u8g2.print("! Air too Dry !");
       else u8g2.print(":) Good Condition");

    } else if (currState == RAW) {
      u8g2.setFont(u8g2_font_6x10_tf);
      u8g2.setCursor(0, 24);  u8g2.print("VPD :"); u8g2.print(vpd, 2); 
      u8g2.setCursor(68, 24); u8g2.print("S_Raw:"); u8g2.print(dispSoilRaw);
      u8g2.setCursor(0, 36);  u8g2.print("DLI :"); u8g2.print(accumulatedDLI, 2);
      u8g2.setCursor(68, 36); u8g2.print("L_Raw:"); u8g2.print(dispLux);
      float ppfd = dispLux * 0.0185;
      u8g2.setCursor(0, 48);  u8g2.print("PPFD:"); u8g2.print((int)ppfd); u8g2.print(" umol");

      drawCheckbox(0, 53, "Valv", vState);
      drawCheckbox(45, 53, "Fan", fState);
      u8g2.drawFrame(85, 53, 10, 10);
      if (wState == "ON") u8g2.drawBox(87, 55, 6, 6);
      u8g2.drawFrame(96, 53, 10, 10);
      if (pState == "ON") u8g2.drawBox(98, 55, 6, 6);
      u8g2.setCursor(108, 61); u8g2.print("LED");
      
    } else if (currState == MENU) {
        u8g2.setFont(u8g2_font_6x10_tf);
        u8g2.drawBox(0, 0, 128, 12);
        u8g2.setDrawColor(0);
        u8g2.setCursor(30, 10); u8g2.print("MENU MODE");
        u8g2.setDrawColor(1);
        for (int i = 0; i < 4; i++) {
          int idx = (menuIdx / 4 * 4) + i;
          if (idx >= MENU_CNT) break;
          if (idx == menuIdx) { 
            u8g2.drawFrame(0, 16+(i*12), 128, 12);
            u8g2.setCursor(6, 26+(i*12)); u8g2.print(">");
          }
          u8g2.setCursor(16, 26+(i*12)); u8g2.print(menus[idx]);
        }
    }
  } while (u8g2.nextPage());

  static unsigned long lastDataSend = 0;
  if (millis() - lastDataSend > 2000) { 
    lastDataSend = millis();
    Serial.print("DATA,");
    Serial.print(t); Serial.print(","); Serial.print(h); Serial.print(",");
    Serial.print(dispSoilRaw); Serial.print(","); Serial.print(dispSoilPct); Serial.print(","); 
    Serial.print(dispLux); Serial.print(","); Serial.println(vpd); 
  }
}