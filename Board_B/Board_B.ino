#include <Stepper.h>

// [핀 설정] GitHub와 실제 연결 상태 반영
const int FAN_PIN = 3;
const int VALVE_PIN = 4;
const int LED_W_PIN = 5;
const int LED_P_PIN = 6;

// [수정] 스테핑 모터 핀: A2, A3, A4, A5
// 28BYJ-48 스테퍼 모터는 보통 IN1, IN3, IN2, IN4 순서로 라이브러리에 넣어야 잘 작동합니다.
// 만약 모터가 덜덜거리고 안 돌면 (stepsPerRev, A2, A3, A4, A5) 순서로 바꿔보세요.
const int stepsPerRev = 2048; 
Stepper myStepper(stepsPerRev, A2, A4, A3, A5); 

bool whiteStatus = false;
bool valveStatus = false;

void setup() {
    Serial.begin(9600);
    pinMode(FAN_PIN, OUTPUT);
    pinMode(VALVE_PIN, OUTPUT);
    pinMode(LED_W_PIN, OUTPUT);
    pinMode(LED_P_PIN, OUTPUT);
    
    // 아날로그 핀을 디지털 출력 모드로 설정
    pinMode(A2, OUTPUT);
    pinMode(A3, OUTPUT);
    pinMode(A4, OUTPUT);
    pinMode(A5, OUTPUT);
    
    myStepper.setSpeed(10); // 요청하신 속도 10
}

void loop() {
    if (Serial.available() > 0) {
        String cmd = Serial.readStringUntil('\n');
        cmd.trim();

        // M0: LED White 토글
        if (cmd == "M0") {
            whiteStatus = !whiteStatus;
            digitalWrite(LED_W_PIN, whiteStatus);
        }
        // M1: 밸브 토글
        else if (cmd == "M1") {
            valveStatus = !valveStatus;
            digitalWrite(VALVE_PIN, valveStatus);
        }
        // M2: LED White 테스트 (2초 켜졌다 꺼짐)
        else if (cmd == "M2") {
            digitalWrite(LED_W_PIN, HIGH); delay(2000); digitalWrite(LED_W_PIN, LOW);
            whiteStatus = false;
        }
        // M3: LED Purple 테스트 (2초 켜졌다 꺼짐)
        else if (cmd == "M3") {
            digitalWrite(LED_P_PIN, HIGH); delay(2000); digitalWrite(LED_P_PIN, LOW);
        }
        // M4: FAN PWM 테스트 (5초간 서서히 빨라졌다가 5초간 느려짐)
        else if (cmd == "M4") {
            for (int i = 0; i <= 255; i += 5) { analogWrite(FAN_PIN, i); delay(100); }
            for (int i = 255; i >= 0; i -= 5) { analogWrite(FAN_PIN, i); delay(100); }
            analogWrite(FAN_PIN, 0);
        }
        // M5: 스테핑 모터 테스트 (CW 1회전, CCW 1회전)
        else if (cmd == "M5") {
            myStepper.step(stepsPerRev);
            delay(500);
            myStepper.step(-stepsPerRev);
        }
    }
}