#include <DHT.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define DHTPIN 8
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// 버튼 핀 설정 (4, 5, 6번)
const int BTN_1 = 4; // 기능 1: TR 제어 (팬/밸브)
const int BTN_2 = 5; // 기능 2: 릴레이 제어 (펌프)
const int BTN_3 = 6; // 기능 3: 모스펫(LED) & 스텝모터

void setup() {
  Serial.begin(9600);
  dht.begin();
  pinMode(BTN_1, INPUT_P_PULLUP);
  pinMode(BTN_2, INPUT_P_PULLUP);
  pinMode(BTN_3, INPUT_P_PULLUP);

  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    for(;;);
  }
  display.clearDisplay();
  display.setTextColor(WHITE);
  display.setTextSize(1);
}

void loop() {
  // 센서 데이터 수집
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  int soil = analogRead(A0);
  int lux = analogRead(A1);

  // 라즈베리파이로 데이터 전송
  Serial.print("D:"); // Data prefix
  Serial.print(t); Serial.print(",");
  Serial.print(h); Serial.print(",");
  Serial.print(soil); Serial.print(",");
  Serial.println(lux);

  // 버튼 입력 체크 (눌리면 RPi로 전송)
  if(digitalRead(BTN_1) == LOW) { Serial.println("B1"); delay(300); }
  if(digitalRead(BTN_2) == LOW) { Serial.println("B2"); delay(300); }
  if(digitalRead(BTN_3) == LOW) { Serial.println("B3"); delay(300); }

  // RPi로부터 OLED 메시지 수신
  if (Serial.available() > 0) {
    String msg = Serial.readStringUntil('\n');
    display.clearDisplay();
    display.setCursor(0,0);
    display.println("[SMART FARM STATUS]");
    display.println("-------------------");
    display.println(msg); 
    display.display();
  }
  delay(200);
}