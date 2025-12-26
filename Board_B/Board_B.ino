#include <Stepper.h>

const int STEPS_PER_REV = 2048;
Stepper myStepper(STEPS_PER_REV, 8, 10, 9, 11);

const int PIN_TR = 3;     // 트랜지스터
const int PIN_RELAY = 4;  // 릴레이
const int PIN_MOSFET = 5; // 모스펫

void setup() {
  Serial.begin(9600);
  pinMode(PIN_TR, OUTPUT);
  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_MOSFET, OUTPUT);
  myStepper.setSpeed(10);
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    if(cmd == '1') digitalWrite(PIN_TR, !digitalRead(PIN_TR));
    if(cmd == '2') digitalWrite(PIN_RELAY, !digitalRead(PIN_RELAY));
    if(cmd == '3') {
      digitalWrite(PIN_MOSFET, !digitalRead(PIN_MOSFET)); // LED 켜고
      myStepper.step(512); // 스텝모터 90도 회전 테스트
    }
    if(cmd == '0') { // 전체 정지
      digitalWrite(PIN_TR, LOW);
      digitalWrite(PIN_RELAY, LOW);
      digitalWrite(PIN_MOSFET, LOW);
    }
  }
}