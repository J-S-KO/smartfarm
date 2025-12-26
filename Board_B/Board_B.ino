#include <Stepper.h>

// 28BYJ-48 스텝모터 기준 1회전 스텝 수
const int STEPS_PER_REV = 2048; 

// 스텝모터 핀 설정: A2, A3, A4, A5 사용
// Stepper 라이브러리는 (스텝수, IN1, IN3, IN2, IN4) 순서가 정석입니다.
Stepper myStepper(STEPS_PER_REV, A2, A4, A3, A5); 

const int PIN_TR = 3;     // 트랜지스터
const int PIN_RELAY = 4;  // 릴레이
const int PIN_MOSFET = 5; // 모스펫

void setup() {
  Serial.begin(9600);
  
  // 구동부 핀 설정
  pinMode(PIN_TR, OUTPUT);
  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_MOSFET, OUTPUT);
  
  // 스텝모터 속도 설정 (5~15 사이가 적당합니다)
  myStepper.setSpeed(10);
  
  // 초기 상태: 모두 OFF
  digitalWrite(PIN_TR, LOW);
  digitalWrite(PIN_RELAY, LOW);
  digitalWrite(PIN_MOSFET, LOW);
}

void loop() {
  if (Serial.available() > 0) {
    char cmd = Serial.read();
    
    // 버튼 1 명령: TR 토글
    if(cmd == '1') {
      digitalWrite(PIN_TR, !digitalRead(PIN_TR));
    }
    // 버튼 2 명령: 릴레이 토글
    else if(cmd == '2') {
      digitalWrite(PIN_RELAY, !digitalRead(PIN_RELAY));
    }
    // 버튼 3 명령: 모스펫 토글 + 스텝모터 테스트
    else if(cmd == '3') {
      digitalWrite(PIN_MOSFET, !digitalRead(PIN_MOSFET));
      // 테스트를 위해 반 바퀴(1024 스텝) 회전
      myStepper.step(1024); 
    }
    // 전체 정지 명령
    else if(cmd == '0') {
      digitalWrite(PIN_TR, LOW);
      digitalWrite(PIN_RELAY, LOW);
      digitalWrite(PIN_MOSFET, LOW);
    }
  }
}