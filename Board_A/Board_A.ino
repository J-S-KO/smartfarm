#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

// [핀 설정] - 사용자 정의 반영
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8);
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
#define PIN_CDS A0
#define PIN_SOIL A1
#define PIN_FAN 3
#define PIN_VALVE 4
#define PIN_LED 5
#define BTN_MOTOR 6   // [변경] 버튼 1: 모터 테스트
#define BTN_ACT 7     // [변경] 버튼 2: 팬/LED 테스트
#define M_IN1 A2
#define M_IN2 A3
#define M_IN3 A4
#define M_IN4 A5

// 변수 설정
float t = 0.0, h = 0.0;
int luxVal = 0, soilVal = 0;
float rcv_vpd = 0.0, rcv_dli = 0.0;
const byte numChars = 32;
char receivedChars[numChars];
boolean newData = false;

// 타이머 변수
unsigned long lastSensorTime = 0;
const long sensorInterval = 2000;
unsigned long lastScreenTime = 0;
const long screenInterval = 100;

// 모터 제어 (Non-blocking)
int motorStepIdx = 0;
unsigned long lastStepTime = 0;
unsigned long stepInterval = 2; 
long targetPos = 0;   
long currentPos = 0;
bool isMotorOpen = false; // 모터 상태 토글용

const int stepsLookup[8][4] = {
  {1, 0, 0, 0}, {1, 1, 0, 0}, {0, 1, 0, 0}, {0, 1, 1, 0},
  {0, 0, 1, 0}, {0, 0, 1, 1}, {0, 0, 0, 1}, {1, 0, 0, 1}
};

void setup() {
  Serial.begin(9600);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_VALVE, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(BTN_MOTOR, INPUT_PULLUP);
  pinMode(BTN_ACT, INPUT_PULLUP);
  pinMode(M_IN1, OUTPUT); pinMode(M_IN2, OUTPUT);
  pinMode(M_IN3, OUTPUT); pinMode(M_IN4, OUTPUT);
  dht.begin();
  u8g2.begin();
}

void loop() {
  unsigned long currentMillis = millis();

  // [1] 파이썬 데이터 수신
  recvWithStartEndMarkers();
  if (newData) { parseData(); newData = false; }

  // [2] 모터 구동 (targetPos가 변하면 자동으로 움직임)
  runStepper();

  // [3] 센서 데이터 전송 (2초 간격)
  if (currentMillis - lastSensorTime >= sensorInterval) {
    lastSensorTime = currentMillis;
    t = dht.readTemperature();
    h = dht.readHumidity();
    luxVal = analogRead(PIN_CDS);
    if (!isnan(t) && !isnan(h)) {
      Serial.print(t, 1); Serial.print(",");
      Serial.print((int)h); Serial.print(",");
      Serial.println(luxVal);
    }
  }

  // [4] 버튼 입력 처리 및 화면 갱신 (0.1초 간격)
  if (currentMillis - lastScreenTime >= screenInterval) {
    lastScreenTime = currentMillis;

    // --- 버튼 1: 모터 테스트 (누를 때마다 위치 변경) ---
    if (digitalRead(BTN_MOTOR) == LOW) {
      isMotorOpen = !isMotorOpen;
      if (isMotorOpen) targetPos = 2048; // 약 반 바퀴 회전
      else targetPos = 0;              // 원위치
      delay(200); // 디바운싱 (임시)
    }

    // --- 버튼 2: 팬/LED 테스트 ---
    if (digitalRead(BTN_ACT) == LOW) {
      digitalWrite(PIN_FAN, HIGH);
      digitalWrite(PIN_LED, HIGH);
    } else {
      digitalWrite(PIN_FAN, LOW);
      digitalWrite(PIN_LED, LOW);
    }

    drawDisplay();
  }
}

// 4상 스텝모터 Non-blocking 구동 함수
void runStepper() {
  if (currentPos == targetPos) {
    digitalWrite(M_IN1, LOW); digitalWrite(M_IN2, LOW);
    digitalWrite(M_IN3, LOW); digitalWrite(M_IN4, LOW);
    return;
  }
  if (millis() - lastStepTime >= stepInterval) {
    lastStepTime = millis();
    if (targetPos > currentPos) {
      currentPos++; motorStepIdx++;
      if (motorStepIdx > 7) motorStepIdx = 0;
    } else {
      currentPos--; motorStepIdx--;
      if (motorStepIdx < 0) motorStepIdx = 7;
    }
    digitalWrite(M_IN1, stepsLookup[motorStepIdx][0]);
    digitalWrite(M_IN2, stepsLookup[motorStepIdx][1]);
    digitalWrite(M_IN3, stepsLookup[motorStepIdx][2]);
    digitalWrite(M_IN4, stepsLookup[motorStepIdx][3]);
  }
}

void drawDisplay() {
  u8g2.firstPage();
  do {
    u8g2.setFont(u8g2_font_6x10_tf);
    u8g2.drawStr(0, 10, "[Smart Farm]");
    u8g2.setCursor(0, 25); u8g2.print("T:"); u8g2.print(t, 1);
    u8g2.print(" H:"); u8g2.print((int)h); u8g2.print("%");
    u8g2.setCursor(0, 40); u8g2.print("VPD:"); u8g2.print(rcv_vpd, 2);
    u8g2.setCursor(0, 55); u8g2.print("Motor:"); 
    u8g2.print(currentPos); u8g2.print(isMotorOpen ? " (Open)" : " (Close)");
  } while (u8g2.nextPage());
}

void recvWithStartEndMarkers() {
  static boolean recvInProgress = false;
  static byte ndx = 0;
  char rc;
  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();
    if (recvInProgress == true) {
      if (rc != '>') {
        receivedChars[ndx] = rc; ndx++;
        if (ndx >= numChars) ndx = numChars - 1;
      } else {
        receivedChars[ndx] = '\0'; recvInProgress = false; ndx = 0; newData = true;
      }
    } else if (rc == '<') { recvInProgress = true; }
  }
}

void parseData() {
  char * strtokIndx = strtok(receivedChars, ",");
  if(strtokIndx != NULL) rcv_vpd = atof(strtokIndx);
  strtokIndx = strtok(NULL, ","); 
  if(strtokIndx != NULL) rcv_dli = atof(strtokIndx);
}