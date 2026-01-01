#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

/* --- 핀 설정 (Pin Config) --- */
const int PIN_DHT = 2;
const int PIN_BTN_RAW = 5;
const int PIN_BTN_MENU = 6;
const int PIN_BTN_OK = 7;

const int SOIL_DRY = 520;   
const int SOIL_WET = 350;   
const int HOME_TIMEOUT = 10000;

U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8);
DHT dht(PIN_DHT, DHT11);

enum State { BOOTING, SCREENSAVER, HOME, RAW, MENU } currState = BOOTING;
unsigned long lastAction = 0;
unsigned long lastScreensaverMove = 0;
unsigned long screensaverStartTime = 0; // 화면보호기 시작 시간 (반복 이동 보장)
int menuIdx = 0;
int screensaverOffsetX = 0; // 화면보호기 X 오프셋 (미세 움직임)
int screensaverOffsetY = 0; // 화면보호기 Y 오프셋 (미세 움직임)
int screensaverDirX = 1; // X 방향 (1 또는 -1)
int screensaverDirY = 1; // Y 방향 (1 또는 -1)
bool systemConnected = false; // 라즈베리파이 연결 상태
bool screenBlinked = false; // 화면 깜빡임 플래그
unsigned long blinkStartTime = 0; // 깜빡임 시작 시간
bool emergencyStop = false; // 비상 정지 상태 (모든 구동계 일시정지)

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
  "EMERGENCY STOP",      // 메뉴 0: 모든 구동계 일시정지 (토글)
  "Water Valve On/Off",  // 메뉴 1: 물 밸브 수동 제어
  "LED(Purple) Test",    // 메뉴 2: 보라색 LED 테스트
  "FAN PWM Test",        // 메뉴 3: 팬 테스트
  "Step Motor Test",     // 메뉴 4: 스테퍼 모터 테스트
  "LED(White) Test",     // 메뉴 5: 화이트 LED 테스트 (예비)
  "Camera Test",         // 메뉴 6: 카메라 촬영
  "System Off"           // 메뉴 7: 시스템 종료
};

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(500);
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

// 64x64 픽셀 딸기 비트맵 데이터 (화면보호기용)
// PROGMEM을 사용하여 플래시 메모리에 저장 (RAM 절약: 512바이트)
const unsigned char epd_bitmap_strawberry[] PROGMEM = {
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x00, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0xc0, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x01, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x07, 0x01, 0xc0, 0xe0, 0x00, 0x00, 
  0x00, 0x00, 0x0f, 0xf1, 0x8f, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x0f, 0xff, 0xff, 0xf0, 0x00, 0x00, 
  0x00, 0x00, 0x07, 0x7f, 0xfe, 0xe0, 0x00, 0x00, 0x00, 0x00, 0x03, 0x87, 0xf1, 0xc0, 0x00, 0x00, 
  0x00, 0x00, 0x03, 0xc3, 0xc3, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x1f, 0xe1, 0x87, 0xf8, 0x00, 0x00, 
  0x00, 0x00, 0x7f, 0xe0, 0x07, 0xfe, 0x00, 0x00, 0x00, 0x01, 0xfe, 0x00, 0x00, 0x7f, 0x80, 0x00, 
  0x00, 0x01, 0xe0, 0x00, 0x00, 0x07, 0x80, 0x00, 0x00, 0x01, 0xf8, 0x00, 0x00, 0x1f, 0x80, 0x00, 
  0x00, 0x00, 0xff, 0xf0, 0x0f, 0xff, 0x00, 0x00, 0x00, 0x01, 0xff, 0xf8, 0x1f, 0xff, 0x80, 0x00, 
  0x00, 0x03, 0x83, 0xf8, 0x1f, 0xc1, 0xc0, 0x00, 0x00, 0x07, 0x80, 0x38, 0x1c, 0x01, 0xe0, 0x00, 
  0x00, 0x07, 0x00, 0x1c, 0x38, 0x00, 0xe0, 0x00, 0x00, 0x06, 0x00, 0x1e, 0x78, 0x00, 0x60, 0x00, 
  0x00, 0x0e, 0x00, 0x0f, 0xf0, 0x00, 0x70, 0x00, 0x00, 0x0e, 0x01, 0x87, 0xe1, 0x80, 0x70, 0x00, 
  0x00, 0x0e, 0x01, 0x83, 0xc1, 0x80, 0x70, 0x00, 0x00, 0x0e, 0x01, 0x80, 0x01, 0x80, 0x70, 0x00, 
  0x00, 0x0e, 0x01, 0x80, 0x01, 0x80, 0x70, 0x00, 0x00, 0x0e, 0x00, 0x00, 0x00, 0x00, 0x70, 0x00, 
  0x00, 0x0e, 0x00, 0x00, 0x00, 0x00, 0x70, 0x00, 0x00, 0x0e, 0x18, 0x18, 0x18, 0x18, 0x70, 0x00, 
  0x00, 0x0e, 0x18, 0x18, 0x18, 0x18, 0x70, 0x00, 0x00, 0x0e, 0x18, 0x18, 0x18, 0x18, 0x70, 0x00, 
  0x00, 0x06, 0x18, 0x18, 0x18, 0x18, 0x60, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x60, 0x00, 
  0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0xe0, 0x00, 
  0x00, 0x03, 0x01, 0x81, 0x81, 0x80, 0xc0, 0x00, 0x00, 0x03, 0x81, 0x81, 0x81, 0x81, 0xc0, 0x00, 
  0x00, 0x03, 0x81, 0x81, 0x81, 0x81, 0xc0, 0x00, 0x00, 0x01, 0xc1, 0x81, 0x81, 0x83, 0x80, 0x00, 
  0x00, 0x01, 0xc0, 0x00, 0x00, 0x03, 0x80, 0x00, 0x00, 0x00, 0xe0, 0x00, 0x00, 0x07, 0x00, 0x00, 
  0x00, 0x00, 0xe0, 0x00, 0x00, 0x07, 0x00, 0x00, 0x00, 0x00, 0x70, 0x18, 0x18, 0x0e, 0x00, 0x00, 
  0x00, 0x00, 0x70, 0x18, 0x18, 0x0e, 0x00, 0x00, 0x00, 0x00, 0x38, 0x18, 0x18, 0x1c, 0x00, 0x00, 
  0x00, 0x00, 0x1c, 0x18, 0x18, 0x38, 0x00, 0x00, 0x00, 0x00, 0x1e, 0x00, 0x00, 0x78, 0x00, 0x00, 
  0x00, 0x00, 0x0f, 0x00, 0x00, 0xf0, 0x00, 0x00, 0x00, 0x00, 0x07, 0x80, 0x01, 0xe0, 0x00, 0x00, 
  0x00, 0x00, 0x03, 0xe0, 0x07, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0xf8, 0x1f, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x7f, 0xfe, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1f, 0xf8, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x03, 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

// 딸기 그리기 함수 (64x64 비트맵 사용, PROGMEM 지원)
// PROGMEM에서 한 줄씩 읽어서 drawBitmap으로 그리기 (RAM 절약: 한 줄만 8바이트 사용)
void drawStrawberry(int x, int y) {
  // 64x64 픽셀 = 8바이트 너비 x 64줄 높이
  // PROGMEM에서 한 줄씩 읽어서 그리기 (RAM 부족 없음)
  uint8_t lineBuffer[8]; // 한 줄 버퍼 (8바이트만 필요)
  
  for (int row = 0; row < 64; row++) {
    // PROGMEM에서 한 줄 읽기
    for (int col = 0; col < 8; col++) {
      lineBuffer[col] = pgm_read_byte(&epd_bitmap_strawberry[row * 8 + col]);
    }
    // 한 줄 그리기
    u8g2.drawBitmap(x, y + row, 8, 1, lineBuffer);
  }
}

// [NEW] 팝업 메시지를 띄우는 함수 (Popup Helper)
void drawPopup(const char* msg) {
  u8g2.firstPage();
  do {
    // 배경을 살짝 지우거나 박스를 그림
    u8g2.setDrawColor(0);
    u8g2.drawBox(10, 20, 108, 24); // 글자 들어갈 공간 지우기
    u8g2.setDrawColor(1);
    u8g2.drawFrame(10, 20, 108, 24); // 테두리 그리기
    
    u8g2.setFont(u8g2_font_6x10_tf);
    // 글자 가운데 정렬 계산
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
      // 간단하고 안정적인 파싱: 콤마로 분리
      int startIdx = 6; // "STATE," 다음부터
      int commaPos[6];
      int found = 0;
      
      // 콤마 위치 찾기
      for (int i = startIdx; i < input.length() && found < 6; i++) {
        if (input.charAt(i) == ',') {
          commaPos[found] = i;
          found++;
        }
      }
      
      // 6개의 콤마를 모두 찾았는지 확인 (STATE,Valve,Fan,LedW,LedP,Hour,Min)
      bool stateParsed = false;
      if (found == 6) {
        vState = input.substring(startIdx, commaPos[0]);
        fState = input.substring(commaPos[0] + 1, commaPos[1]);
        wState = input.substring(commaPos[1] + 1, commaPos[2]);
        pState = input.substring(commaPos[2] + 1, commaPos[3]);
        sysHour = input.substring(commaPos[3] + 1, commaPos[4]).toInt();
        sysMin = input.substring(commaPos[4] + 1, commaPos[5]).toInt();
        stateParsed = true;
      } else if (found == 5) {
        // 마지막 콤마가 없을 수도 있음 (개행 문자로 끝나는 경우)
        vState = input.substring(startIdx, commaPos[0]);
        fState = input.substring(commaPos[0] + 1, commaPos[1]);
        wState = input.substring(commaPos[1] + 1, commaPos[2]);
        pState = input.substring(commaPos[2] + 1, commaPos[3]);
        sysHour = input.substring(commaPos[3] + 1, commaPos[4]).toInt();
        sysMin = input.substring(commaPos[4] + 1).toInt();
        stateParsed = true;
      }
      
      // 라즈베리파이 연결 확인: STATE 명령이 성공적으로 파싱되면 연결된 것으로 간주
      // (시간이 00:00이어도 STATE 명령 수신 자체가 연결 증거)
      if (!systemConnected && stateParsed) {
        systemConnected = true;
        screenBlinked = false; // 화면 깜빡임 트리거
        blinkStartTime = millis(); // 깜빡임 시작 시간 기록
        if (currState == BOOTING) {
          screensaverStartTime = millis();
          screensaverOffsetX = 0;
          screensaverOffsetY = 0;
          screensaverDirX = 1;
          screensaverDirY = 1;
          currState = SCREENSAVER;
          lastScreensaverMove = millis();
        }
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

  // 버튼1 (RAW 버튼): SCREENSAVER -> HOME -> RAW -> HOME 순환 (부팅 중에는 작동 안 함)
  if (digitalRead(PIN_BTN_RAW) == LOW && currState != BOOTING) {
    if (currState == SCREENSAVER) {
      currState = HOME;
    } else if (currState == HOME) {
      currState = RAW;
    } else if (currState == RAW) {
      currState = HOME;
    }
    lastAction = millis();
    delay(200);
  }
  
  // 버튼2 (MENU 버튼): 메뉴 진입
  if (digitalRead(PIN_BTN_MENU) == LOW) {
    if (currState != MENU) { 
      currState = MENU; 
      menuIdx = 0; 
    } else {
      menuIdx = (menuIdx + 1) % MENU_CNT;
    }
    lastAction = millis(); 
    delay(200);
  }
  
  // 메뉴에서 10초 동안 아무 동작이 없으면 화면보호기로 돌아가기
  if (currState == MENU && millis() - lastAction > HOME_TIMEOUT) {
    screensaverStartTime = millis();
    screensaverOffsetX = 0;
    screensaverOffsetY = 0;
    screensaverDirX = 1;
    screensaverDirY = 1;
    currState = SCREENSAVER;
    lastScreensaverMove = millis();
  }
  
  // [업그레이드된 버튼 처리]
  // OK 버튼: 메뉴 모드에서는 메뉴 실행, 메뉴가 아닐 때는 LED 토글
  if (digitalRead(PIN_BTN_OK) == LOW) {
    if (currState == MENU) {
      // 메뉴 모드: 메뉴 실행
      // 1. 피드백 메시지 결정
      const char* msg = "Sending...";
      if (menuIdx == 0) {
        // 비상 정지 토글
        emergencyStop = !emergencyStop;
        msg = emergencyStop ? "EMERGENCY STOP" : "RESUME";
      } else if (menuIdx == 6) msg = "Say Cheese!";    // 카메라 테스트 시
      else if (menuIdx == 7) msg = "Power OFF..."; // 종료 시
      else msg = "Processing...";               // 일반 제어 시

      // 2. 화면에 팝업 띄우기 (즉시)
      drawPopup(msg);

      // 3. 시리얼 명령 전송
      if (menuIdx == 7) Serial.println(F("SYS_OFF"));
      else if (menuIdx == 0) {
        // 비상 정지 명령 전송
        if (emergencyStop) {
          Serial.println(F("EMERGENCY_STOP"));
        } else {
          Serial.println(F("EMERGENCY_RESUME"));
        }
      } else { 
        Serial.print(F("CMD_M")); Serial.println(menuIdx); 
      }
      
      // 4. 사용자가 메시지를 볼 수 있게 1초 대기
      delay(1000); 
      
      lastAction = millis();
    } else if (currState != BOOTING) {
      // 메뉴가 아닐 때 (HOME, RAW, SCREENSAVER): LED 토글
      // 안전: 부팅 중에는 작동 안 함
      Serial.println(F("CMD_M5")); // LED 토글 명령 (메뉴 5번으로 매핑)
      lastAction = millis();
      delay(200); // 디바운싱
    }
  }
  
  // 10초 동안 아무 동작이 없으면 화면보호기 모드로 전환 (부팅 중이 아닐 때만)
  if (millis() - lastAction > HOME_TIMEOUT && currState != MENU && currState != BOOTING) {
    if (currState != SCREENSAVER) {
      // 화면보호기로 처음 전환될 때 시작 시간 기록 및 오프셋 초기화
      screensaverStartTime = millis();
      screensaverOffsetX = 0;
      screensaverOffsetY = 0;
      screensaverDirX = 1;
      screensaverDirY = 1;
      lastScreensaverMove = millis(); // 처음 전환 시에만 타이머 초기화
    }
    currState = SCREENSAVER;
  }
  
  // 화면보호기: 1초마다 움직임 (부드러운 애니메이션)
  // 화면보호기 모드가 활성화되어 있는 동안 계속 반복적으로 이동
  if (currState == SCREENSAVER && millis() - lastScreensaverMove > 1000) {
    // X 방향 움직임: 화면 중앙(32) 기준으로 -30 ~ +30 픽셀 범위에서 이동
    screensaverOffsetX += screensaverDirX;
    if (screensaverOffsetX >= 30) {
      screensaverDirX = -1; // 오른쪽 경계 도달 시 왼쪽으로
    } else if (screensaverOffsetX <= -30) {
      screensaverDirX = 1;  // 왼쪽 경계 도달 시 오른쪽으로
    }
    
    // Y 방향 움직임: 화면 상단(0)에 고정 (비트맵 높이 64 = 화면 높이 64이므로 오프셋 0 유지)
    // 화면을 벗어나지 않도록 Y 오프셋은 항상 0으로 유지
    screensaverOffsetY = 0;
    
    lastScreensaverMove = millis(); // 다음 이동 시간 업데이트 (반복 보장)
  }

  // --- 화면 그리기 ---
  u8g2.firstPage();
  do {
    // 부팅 중이거나 화면보호기가 아닐 때만 상단 정보 표시
    if (currState != BOOTING && currState != SCREENSAVER) {
      u8g2.setFont(u8g2_font_helvB08_tr);
      u8g2.setCursor(0, 10);
      if(sysHour < 10) u8g2.print("0"); u8g2.print(sysHour); u8g2.print(":");
      if(sysMin < 10) u8g2.print("0"); u8g2.print(sysMin);
      
      // 비상 정지 상태 표시 (우측 상단)
      if (emergencyStop) {
        u8g2.setCursor(85, 10);
        u8g2.print("!STOP!");
      } else {
        u8g2.setCursor(55, 10);
        if(isnan(t)) { u8g2.print("SensErr"); }
        else {
          u8g2.print("T:"); u8g2.print((int)t); 
          u8g2.print(" H:"); u8g2.print((int)h); u8g2.print("%");
        }
      }
      u8g2.drawHLine(0, 13, 128);
    }
    
    // 화면 깜빡임 효과 (라즈베리파이 연결 시 - 200ms 동안 화면 지우기)
    if (systemConnected && !screenBlinked && (millis() - blinkStartTime < 200)) {
      // 깜빡임 중: 화면 지우기
      u8g2.setDrawColor(0);
      u8g2.drawBox(0, 0, 128, 64);
      u8g2.setDrawColor(1);
    } else if (systemConnected && !screenBlinked && (millis() - blinkStartTime >= 200)) {
      screenBlinked = true; // 깜빡임 완료
    }

    if (currState == BOOTING) {
      // 부팅 중 메시지
      u8g2.setFont(u8g2_font_helvB12_tr);
      int strW = u8g2.getStrWidth("Booting..");
      u8g2.setCursor(64 - (strW / 2), 32);
      u8g2.print("Booting..");
      
    } else if (currState == SCREENSAVER) {
      // 화면보호기: 딸기 하나가 화면을 돌아다님 (64x64 비트맵, 화면 중앙 배치)
      // 화면 너비 128, 비트맵 너비 64 -> 중앙: (128-64)/2 = 32
      drawStrawberry(32 + screensaverOffsetX, 0 + screensaverOffsetY);
      
    } else if (currState == HOME) {
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