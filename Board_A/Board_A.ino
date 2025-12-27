#include <Arduino.h>
#include <U8g2lib.h>
#include <DHT.h>

// [사용자 튜닝 파라미터] - GitHub 원본 기준
const int SOIL_DRY = 530, SOIL_WET = 300;
const int LUX_DARK = 900, LUX_BRIGHT = 100;
const float VPD_OPT = 1.0, VPD_RANGE = 0.6;
const int SOIL_OPT = 60;
const int LUX_OPT = 500;
const unsigned long UI_TIMEOUT = 5000;

// GitHub 핀 설정 반영
U8G2_SH1106_128X64_NONAME_1_4W_HW_SPI u8g2(U8G2_R0, 10, 9, 8);
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

const int BTN_RAW = 5, BTN_MENU = 6, BTN_OK = 7;
enum State { HOME, RAW, MENU } currState = HOME; // DEFAULT -> HOME
unsigned long lastAction = 0;
int menuIdx = 0;
const int MENU_CNT = 7;
const char* menus[] = {
    "LED(White) On/Off", "Water Valve On/Off", "LED(White) Test", 
    "LED(Purple) Test", "FAN PWM Test", "Step Motor Test", "System Off"
};

float t, h, vpd;
int soil, lux, soilPct;

String getGauge(float val, float opt, float range) {
    int pos = map(constrain(val * 100, (opt - range) * 100, (opt + range) * 100), 
                  (opt - range) * 100, (opt + range) * 100, 0, 8);
    String g = "---------"; g.setCharAt(pos, '*'); return g;
}

float calcVPD(float T, float H) {
    float es = 0.61078 * exp((17.27 * T) / (T + 237.3));
    return es * (1.0 - (H / 100.0));
}

void setup() {
    Serial.begin(9600); dht.begin(); u8g2.begin();
    pinMode(BTN_RAW, INPUT_PULLUP); pinMode(BTN_MENU, INPUT_PULLUP); pinMode(BTN_OK, INPUT_PULLUP);
}

void loop() {
    t = dht.readTemperature(); h = dht.readHumidity();
    soil = analogRead(A1); lux = analogRead(A0);
    soilPct = map(constrain(soil, SOIL_WET, SOIL_DRY), SOIL_DRY, SOIL_WET, 0, 100);
    if (!isnan(t) && !isnan(h)) vpd = calcVPD(t, h);

    if (digitalRead(BTN_RAW) == LOW) { currState = RAW; lastAction = millis(); delay(200); }
    if (digitalRead(BTN_MENU) == LOW) {
        if (currState != MENU) { currState = MENU; menuIdx = 0; }
        else menuIdx = (menuIdx + 1) % MENU_CNT;
        lastAction = millis(); delay(200);
    }
    if (digitalRead(BTN_OK) == LOW && currState == MENU) {
        if (menuIdx == 6) Serial.println("SYS_OFF"); // System Off 처리
        else Serial.println("CMD_M" + String(menuIdx)); // 보드 B 전달용
        lastAction = millis(); delay(500);
    }

    if (millis() - lastAction > UI_TIMEOUT) currState = HOME;

    u8g2.firstPage();
    do {
        u8g2.setFont(u8g2_font_6x10_tf);
        if (currState == HOME) {
            u8g2.setCursor(0, 10); u8g2.print("T:" + String(t, 1) + "C H:" + String((int)h) + "%");
            u8g2.setCursor(0, 23); u8g2.print("Soil:  " + getGauge(soilPct, SOIL_OPT, 30));
            u8g2.setCursor(0, 36); u8g2.print("Light: " + getGauge(lux, LUX_OPT, 300));
            u8g2.setCursor(0, 49); u8g2.print("VPD:   " + getGauge(vpd, VPD_OPT, 0.6));
            u8g2.setCursor(0, 62); 
            if (vpd > 1.5) u8g2.print("WARN: TOO DRY!");
            else if (soilPct < 30) u8g2.print("WARN: NEED WATER");
            else u8g2.print("SYSTEM HEALTHY");
        } 
        else if (currState == RAW) {
            u8g2.drawStr(0, 10, "[ SENSOR RAW ]");
            u8g2.setCursor(0, 25); u8g2.print("T/H: " + String(t) + "/" + String(h));
            u8g2.setCursor(0, 38); u8g2.print("Soil: " + String(soil) + " (" + String(soilPct) + "%)");
            u8g2.setCursor(0, 51); u8g2.print("Lux: " + String(lux));
        }
        else if (currState == MENU) {
            u8g2.drawStr(0, 10, "[ SETTING MENU ]");
            for (int i = 0; i < 4; i++) {
                int idx = (menuIdx / 4 * 4) + i;
                if (idx >= MENU_CNT) break;
                if (idx == menuIdx) { u8g2.drawBox(0, 14 + (i * 12), 128, 12); u8g2.setDrawColor(0); }
                else u8g2.setDrawColor(1);
                u8g2.setCursor(4, 24 + (i * 12)); u8g2.print(menus[idx]);
            }
            u8g2.setDrawColor(1);
        }
    } while (u8g2.nextPage());
}