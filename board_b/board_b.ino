#include <Stepper.h>
#include <Adafruit_NeoPixel.h>

/* --- 사용자 설정 변수 (User Config) --- */
const int PIN_FAN = 3;
const int PIN_VALVE = 4;
const int PIN_LED_W = 5;
const int PIN_NEOPIXEL = 6;
const int NUM_PIXELS = 60;
const int STEP_SPEED = 10;
const uint32_t GROW_PURPLE = Adafruit_NeoPixel::Color(200, 0, 255, 10); // 식물 생장용 보라색 (RGBW)

// LED 페이드 설정 (10분 = 600초)
const unsigned long LED_FADE_DURATION_MS = 600000;  // 10분 (밀리초)
const unsigned long LED_FADE_STEP_MS = 100;         // 0.1초마다 업데이트

/* --- 장치 초기화 (Device Init) --- */
Adafruit_NeoPixel pixels(NUM_PIXELS, PIN_NEOPIXEL, NEO_GRBW + NEO_KHZ800);
Stepper myStepper(2048, A2, A4, A3, A5); 

/* --- 상태 및 타이머 (State & Timer) --- */
unsigned long actionStartTime = 0;
int currentMode = -1; // -1: 대기, 2: 화이트테스트, 3: 식물등테스트, 4: 팬테스트
bool whiteStatus = false;
bool valveStatus = false;
bool emergencyStop = false; // 비상 정지 상태 (모든 구동계 일시정지)

// LED 밝기 상태 (0=OFF, 1=30%, 2=50%, 3=100%)
int ledBrightnessLevel = 0;  // 0: OFF, 1: 30%, 2: 50%, 3: 100%
const int LED_BRIGHTNESS_VALUES[] = {0, 77, 128, 255}; // PWM 값 (0%, 30%, 50%, 100%)

// White LED 페이드 상태
bool ledFadeActive = false;
unsigned long ledFadeStartTime = 0;
int ledFadeStartBrightness = 0;  // 페이드 시작 시 밝기
int ledFadeTargetBrightness = 0; // 페이드 목표 밝기
int ledFadeCurrentBrightness = 0; // 현재 페이드 중 밝기

// Purple LED 페이드 상태 (NeoPixel)
bool purpleFadeActive = false;
unsigned long purpleFadeStartTime = 0;
int purpleFadeStartBrightness = 0;  // 페이드 시작 시 밝기 (0-255)
int purpleFadeTargetBrightness = 0; // 페이드 목표 밝기 (0-255)
int purpleFadeCurrentBrightness = 0; // 현재 페이드 중 밝기 (0-255)
const int PURPLE_MAX_BRIGHTNESS = 150; // Purple LED 최대 밝기 (전류 소모 제한)

void setup() {
  Serial.begin(9600);
  pinMode(PIN_FAN, OUTPUT);
  pinMode(PIN_VALVE, OUTPUT);
  pinMode(PIN_LED_W, OUTPUT);
  pinMode(A2, OUTPUT); pinMode(A3, OUTPUT); pinMode(A4, OUTPUT); pinMode(A5, OUTPUT);
  
  pixels.begin();
  pixels.setBrightness(0); // 초기 상태: OFF
  pixels.show();
  myStepper.setSpeed(STEP_SPEED);
  
  // LED 초기 상태: OFF
  analogWrite(PIN_LED_W, 0);
  purpleFadeCurrentBrightness = 0;
}

void updateLedFade() {
  // 페이드가 활성화되어 있지 않으면 리턴
  if (!ledFadeActive) return;
  
  unsigned long now = millis();
  unsigned long elapsed = now - ledFadeStartTime;
  
  // 페이드 완료 체크
  if (elapsed >= LED_FADE_DURATION_MS) {
    // 페이드 완료: 목표 밝기로 설정
    ledFadeCurrentBrightness = ledFadeTargetBrightness;
    analogWrite(PIN_LED_W, ledFadeCurrentBrightness);
    ledFadeActive = false;
    
    // 밝기 레벨 업데이트
    if (ledFadeTargetBrightness == 0) {
      ledBrightnessLevel = 0;
    } else if (ledFadeTargetBrightness == LED_BRIGHTNESS_VALUES[1]) {
      ledBrightnessLevel = 1;
    } else if (ledFadeTargetBrightness == LED_BRIGHTNESS_VALUES[2]) {
      ledBrightnessLevel = 2;
    } else if (ledFadeTargetBrightness == LED_BRIGHTNESS_VALUES[3]) {
      ledBrightnessLevel = 3;
    }
    return;
  }
  
  // 페이드 진행 중: 선형 보간으로 밝기 계산
  float progress = (float)elapsed / (float)LED_FADE_DURATION_MS;
  ledFadeCurrentBrightness = ledFadeStartBrightness + 
                            (int)((ledFadeTargetBrightness - ledFadeStartBrightness) * progress);
  
  // PWM 값 제한 (0-255)
  if (ledFadeCurrentBrightness < 0) ledFadeCurrentBrightness = 0;
  if (ledFadeCurrentBrightness > 255) ledFadeCurrentBrightness = 255;
  
  analogWrite(PIN_LED_W, ledFadeCurrentBrightness);
}

void startLedFade(int targetBrightness) {
  // 현재 밝기 확인 (페이드 중이면 현재 밝기, 아니면 현재 레벨의 밝기)
  int currentBrightness = ledFadeActive ? ledFadeCurrentBrightness : LED_BRIGHTNESS_VALUES[ledBrightnessLevel];
  
  // 목표 밝기가 현재 밝기와 같으면 페이드 불필요
  if (currentBrightness == targetBrightness) {
    ledFadeActive = false;
    return;
  }
  
  // 페이드 시작
  ledFadeStartTime = millis();
  ledFadeStartBrightness = currentBrightness;
  ledFadeTargetBrightness = targetBrightness;
  ledFadeActive = true;
}

void stopLedFade() {
  // 페이드 중단: 페이드 비활성화
  if (ledFadeActive) {
    ledFadeActive = false;
    // 현재 밝기는 그대로 유지 (ledFadeCurrentBrightness)
  }
}

void setLedBrightnessImmediate(int level) {
  // 즉시 밝기 변경 (페이드 없음)
  stopLedFade(); // 페이드 중단
  ledBrightnessLevel = level;
  if (level >= 0 && level <= 3) {
    int targetBrightness = LED_BRIGHTNESS_VALUES[level];
    analogWrite(PIN_LED_W, targetBrightness);
    // ledFadeCurrentBrightness도 업데이트하여 updateLedFade()가 덮어쓰지 않도록
    // (updateLedFade()는 ledFadeActive가 false면 실행 안 하지만, 안전을 위해)
    ledFadeCurrentBrightness = targetBrightness;
  } else {
    // 잘못된 레벨이면 0으로 설정
    analogWrite(PIN_LED_W, 0);
    ledFadeCurrentBrightness = 0;
  }
}

void cycleLedBrightness() {
  // 30% - 50% - 100% - OFF 순서로 순환
  int nextLevel = (ledBrightnessLevel + 1) % 4; // 0->1->2->3->0
  setLedBrightnessImmediate(nextLevel);
}

// Purple LED 페이드 업데이트
void updatePurpleFade() {
  // 페이드가 활성화되어 있지 않으면 리턴
  if (!purpleFadeActive) return;
  
  unsigned long now = millis();
  unsigned long elapsed = now - purpleFadeStartTime;
  
  // 페이드 완료 체크
  if (elapsed >= LED_FADE_DURATION_MS) {
    // 페이드 완료: 목표 밝기로 설정
    purpleFadeCurrentBrightness = purpleFadeTargetBrightness;
    pixels.setBrightness(purpleFadeCurrentBrightness);
    if (purpleFadeCurrentBrightness > 0) {
      // LED 켜기
      for(int i=0; i<NUM_PIXELS; i++) {
        pixels.setPixelColor(i, GROW_PURPLE);
      }
    } else {
      // LED 끄기
      pixels.clear();
    }
    pixels.show();
    purpleFadeActive = false;
    return;
  }
  
  // 페이드 진행 중: 선형 보간으로 밝기 계산
  float progress = (float)elapsed / (float)LED_FADE_DURATION_MS;
  purpleFadeCurrentBrightness = purpleFadeStartBrightness + 
                                (int)((purpleFadeTargetBrightness - purpleFadeStartBrightness) * progress);
  
  // 밝기 값 제한 (0-255)
  if (purpleFadeCurrentBrightness < 0) purpleFadeCurrentBrightness = 0;
  if (purpleFadeCurrentBrightness > PURPLE_MAX_BRIGHTNESS) purpleFadeCurrentBrightness = PURPLE_MAX_BRIGHTNESS;
  
  // NeoPixel 밝기 업데이트
  pixels.setBrightness(purpleFadeCurrentBrightness);
  if (purpleFadeCurrentBrightness > 0) {
    // LED 켜기
    for(int i=0; i<NUM_PIXELS; i++) {
      pixels.setPixelColor(i, GROW_PURPLE);
    }
  } else {
    // LED 끄기
    pixels.clear();
  }
  pixels.show();
}

void startPurpleFade(int targetBrightness) {
  // 현재 밝기 확인 (페이드 중이면 현재 밝기, 아니면 저장된 현재 밝기)
  int currentBrightness = purpleFadeActive ? purpleFadeCurrentBrightness : purpleFadeCurrentBrightness;
  
  // 목표 밝기 제한
  if (targetBrightness > PURPLE_MAX_BRIGHTNESS) targetBrightness = PURPLE_MAX_BRIGHTNESS;
  if (targetBrightness < 0) targetBrightness = 0;
  
  // 목표 밝기가 현재 밝기와 같으면 페이드 불필요
  if (currentBrightness == targetBrightness) {
    purpleFadeActive = false;
    return;
  }
  
  // 페이드 시작
  purpleFadeStartTime = millis();
  purpleFadeStartBrightness = currentBrightness;
  purpleFadeTargetBrightness = targetBrightness;
  purpleFadeActive = true;
}

void stopPurpleFade() {
  // 페이드 중단: 현재 밝기 유지하고 페이드 비활성화
  if (purpleFadeActive) {
    purpleFadeActive = false;
    // 현재 밝기는 그대로 유지 (purpleFadeCurrentBrightness)
  }
}

void setPurpleBrightnessImmediate(int brightness) {
  // 즉시 밝기 변경 (페이드 없음)
  stopPurpleFade(); // 페이드 중단
  if (brightness > PURPLE_MAX_BRIGHTNESS) brightness = PURPLE_MAX_BRIGHTNESS;
  if (brightness < 0) brightness = 0;
  
  purpleFadeCurrentBrightness = brightness;
  pixels.setBrightness(brightness);
  if (brightness > 0) {
    for(int i=0; i<NUM_PIXELS; i++) {
      pixels.setPixelColor(i, GROW_PURPLE);
    }
  } else {
    pixels.clear();
  }
  pixels.show();
}

void loop() {
  // LED 페이드 업데이트 (매 루프마다 체크)
  updateLedFade();
  updatePurpleFade();
  
  // 1. 시리얼 명령어 처리 (비차단 방식)
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();

    // 메뉴 명령 처리 (비상 정지 중에도 수동 제어는 가능)
    if (cmd == "M0") { 
      // 메뉴 0번은 비상 정지 (board_a에서 처리, 여기서는 무시)
    }
    else if (cmd == "M1") { 
      // 물 밸브 수동 제어 (비상 정지 중에도 수동 제어 가능)
      valveStatus = !valveStatus; 
      digitalWrite(PIN_VALVE, valveStatus); 
    }
    else if (cmd == "M2") { 
      // 보라색 LED 테스트 (비상 정지 중에도 테스트 가능)
      currentMode = 3; 
      actionStartTime = millis(); 
    }
    else if (cmd == "M3") { 
      // 팬 테스트 (비상 정지 중에는 작동 안 함)
      if (!emergencyStop) {
        currentMode = 4; 
        actionStartTime = millis(); 
      }
    }
    else if (cmd == "M4") { 
      // 스테퍼 모터 테스트 (비상 정지 중에는 작동 안 함)
      if (!emergencyStop) {
        myStepper.step(2048); 
        delay(500); 
        myStepper.step(-2048); 
      }
    }
    else if (cmd == "M5") { 
      // LED 밝기 순환 (30% - 50% - 100% - OFF)
      // 페이드 중이면 즉시 중단하고 새 밝기로 변경
      cycleLedBrightness();
    }
    // 자동 제어용 명령어 (automation.py에서 사용)
    else if (cmd == "FAN_ON") { 
      if (!emergencyStop) { // 비상 정지 중이 아니면만 작동
        analogWrite(PIN_FAN, 255); 
      }
    }
    else if (cmd == "FAN_OFF") { analogWrite(PIN_FAN, 0); }
    // LED 페이드 명령어 (자동화 시스템에서 사용)
    else if (cmd == "LED_FADE_ON") {
      if (!emergencyStop) {
        // 페이드 중이면 중단하고 새 페이드 시작
        startLedFade(LED_BRIGHTNESS_VALUES[3]); // 100%로 페이드 인
      }
    }
    else if (cmd == "LED_FADE_OFF") {
      // 비상 정지 중이 아니면 페이드 아웃, 비상 정지 중이면 즉시 OFF
      if (emergencyStop) {
        setLedBrightnessImmediate(0);
      } else {
        startLedFade(0); // OFF로 페이드 아웃
      }
    }
    // Purple LED 페이드 명령어 (자동화 시스템에서 사용)
    else if (cmd == "PURPLE_FADE_ON") {
      if (!emergencyStop) {
        // 페이드 중이면 중단하고 새 페이드 시작
        startPurpleFade(PURPLE_MAX_BRIGHTNESS); // 최대 밝기로 페이드 인
      }
    }
    else if (cmd == "PURPLE_FADE_OFF") {
      // 비상 정지 중이 아니면 페이드 아웃, 비상 정지 중이면 즉시 OFF
      if (emergencyStop) {
        setPurpleBrightnessImmediate(0);
      } else {
        startPurpleFade(0); // OFF로 페이드 아웃
      }
    }
    // LED 즉시 명령어 (웹 UI 및 수동 제어용, 페이드 없음)
    else if (cmd == "LED_ON") {
      if (!emergencyStop) {
        setLedBrightnessImmediate(3); // 100%로 즉시 ON
      }
    }
    else if (cmd == "LED_OFF") {
      setLedBrightnessImmediate(0); // 즉시 OFF
    }
    else if (cmd == "PURPLE_ON") {
      if (!emergencyStop) {
        setPurpleBrightnessImmediate(PURPLE_MAX_BRIGHTNESS); // 최대 밝기로 즉시 ON
      }
    }
    else if (cmd == "PURPLE_OFF") {
      setPurpleBrightnessImmediate(0); // 즉시 OFF
    }
    // 비상 정지 명령어
    else if (cmd == "EMERGENCY_STOP") {
      emergencyStop = true;
      // 모든 구동계 즉시 정지 (페이드 중단)
      stopLedFade();
      stopPurpleFade();
      analogWrite(PIN_FAN, 0);        // 팬 OFF
      digitalWrite(PIN_VALVE, LOW);   // 밸브 OFF
      setLedBrightnessImmediate(0);   // White LED 즉시 OFF
      setPurpleBrightnessImmediate(0); // Purple LED 즉시 OFF
      valveStatus = false;
      // 스테퍼 모터는 현재 움직이는 중이면 정지 불가 (하지만 다음 명령은 무시됨)
    }
    else if (cmd == "EMERGENCY_RESUME") {
      emergencyStop = false;
      // 재개 시 자동화 시스템이 필요에 따라 다시 켤 수 있음
    }
    // 커튼 제어 명령어 (스텝 수 포함: CURTAIN_OPEN:2048 또는 CURTAIN_CLOSE:-2048)
    // 비상 정지 중에는 커튼 제어 안 됨
    else if (cmd.startsWith("CURTAIN_OPEN:")) {
      if (!emergencyStop) {
        int steps = cmd.substring(13).toInt(); // "CURTAIN_OPEN:" 다음 숫자
        myStepper.step(steps);
      }
    }
    else if (cmd.startsWith("CURTAIN_CLOSE:")) {
      if (!emergencyStop) {
        int steps = cmd.substring(14).toInt(); // "CURTAIN_CLOSE:" 다음 숫자
        myStepper.step(steps);
      }
    }
  }

  // 2. 시간 기반 비차단 동작 (Non-blocking Logic)
  unsigned long now = millis();
  unsigned long diff = now - actionStartTime;

  if (currentMode == 2) { // White LED 3초 테스트
    if (diff >= 3000) { 
      setLedBrightnessImmediate(0);
      currentMode = -1; 
    }
  } 
  else if (currentMode == 3) { // Grow Purple NeoPixel 3초 테스트
    if (diff < 3000) {
      for(int i=0; i<NUM_PIXELS; i++) pixels.setPixelColor(i, GROW_PURPLE);
      pixels.show();
    } else {
      pixels.clear(); pixels.show(); currentMode = -1;
    }
  }
  else if (currentMode == 4) { // FAN PWM 10초 가감속 테스트
    if (diff < 5000) analogWrite(PIN_FAN, map(diff, 0, 5000, 0, 255));
    else if (diff < 10000) analogWrite(PIN_FAN, map(diff, 5000, 10000, 255, 0));
    else { analogWrite(PIN_FAN, 0); currentMode = -1; }
  }
}
