#include <Stepper.h>
#include <Adafruit_NeoPixel.h>

/* --- 사용자 설정 변수 --- */
const int PIN_FAN = 3;
const int PIN_VALVE = 4;
const int PIN_LED_W = 5;
const int PIN_NEOPIXEL = 6;
const int NUM_PIXELS = 60;
const int STEP_SPEED = 10;
const uint32_t GROW_PURPLE = Adafruit_NeoPixel::Color(200, 0, 255, 10); // 식물 생장용 보라색(RGBW)

/* --- 장치 초기화 --- */
Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRBW + NEO_KHZ800);
Stepper myStepper(2048, A2, A4, A3, A5); 

/* --- 상태 및 타이머 --- */
unsigned long actionStartTime = 0;
int currentMode = -1; // -1: 대기, 2: 화이트테스트, 3: 퍼플테스트, 4: 팬테스트
bool whiteStatus = false;
bool valveStatus = false;

void setup() {
  Serial.begin(9600);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_VALVE, OUTPUT);
  pinMode(PIN_LED_W, OUTPUT);
  pinMode(A2, OUTPUT); pinMode(A3, OUTPUT); pinMode(A4, OUTPUT); pinMode(A5, OUTPUT);
  
  pixels.begin();
  pixels.setBrightness(150); // 전류 소모 억제를 위해 60% 밝기 제한
  pixels.show();
  myStepper.setSpeed(STEP_SPEED);
}

void loop() {
  // 1. 시리얼 명령 처리 (비차단)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    if (cmd == "M0") { whiteStatus = !whiteStatus; digitalWrite(PIN_LED_W, whiteStatus); }
    else if (cmd == "M1") { valveStatus = !valveStatus; digitalWrite(PIN_VALVE, valveStatus); }
    else if (cmd == "M2") { currentMode = 2; actionStartTime = millis(); digitalWrite(PIN_LED_W, HIGH); }
    else if (cmd == "M3") { currentMode = 3; actionStartTime = millis(); }
    else if (cmd == "M4") { currentMode = 4; actionStartTime = millis(); }
    else if (cmd == "M5") { myStepper.step(2048); delay(500); myStepper.step(-2048); }
    // 자동 제어용 팬 명령 (automation.py에서 사용)
    else if (cmd == "FAN_ON") { analogWrite(PIN_FAN, 255); }
    else if (cmd == "FAN_OFF") { analogWrite(PIN_FAN, 0); }
  }

  // 2. 시간 기반 비차단 동작
  unsigned long now = millis();
  unsigned long diff = now - actionStartTime;

  if (currentMode == 2) { // White LED 3초
    if (diff >= 3000) { digitalWrite(PIN_LED_W, LOW); currentMode = -1; }
  } 
  else if (currentMode == 3) { // Grow Purple NeoPixel 3초
    if (diff < 3000) {
      for(int i=0; i<NUM_PIXELS; i++) pixels.setPixelColor(i, GROW_PURPLE);
      pixels.show();
    } else {
      pixels.clear(); pixels.show(); currentMode = -1;
    }
  }
  else if (currentMode == 4) { // FAN PWM 10초 가감속
    if (diff < 5000) analogWrite(PIN_FAN, map(diff, 0, 5000, 0, 255));
    else if (diff < 10000) analogWrite(PIN_FAN, map(diff, 5000, 10000, 255, 0));
    else { analogWrite(PIN_FAN, 0); currentMode = -1; }
  }
}