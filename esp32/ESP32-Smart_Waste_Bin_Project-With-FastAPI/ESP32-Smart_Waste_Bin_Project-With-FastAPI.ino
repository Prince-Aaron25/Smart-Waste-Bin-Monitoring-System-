
#define BLYNK_TEMPLATE_ID "TMPL6Lw4EwroV"
#define BLYNK_TEMPLATE_NAME "Blynk Smart Waste Bin Monitoring System"
#define BLYNK_AUTH_TOKEN "F8qkcF89V4tPxnE-4aAjIyS_iuCv951-"

#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <BlynkSimpleEsp32.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// WIFI AND FASTAPI
char ssid[] = "Galaxy S21 5G 7306";
char pass[] = "gimmedevwallet";

const char* API_URL =
  "http://10.101.73.225:8000/api/readings";

const char* API_KEY = "DuXDvZteNCVskO0WH1XtDwEYn97xWMBOWHzuVJtJCkw";
const int DEVICE_ID = 1;

// PINS (UNCHANGED)
#define TRIG_PIN 32
#define ECHO_PIN 33
#define LED_PIN 27
#define SDA_PIN 21
#define SCL_PIN 22

// BIN CALIBRATION (UNCHANGED)
const float EMPTY_DISTANCE = 23.0;
const float FULL_DISTANCE = 1.0;

// LCD
LiquidCrystal_I2C lcd(0x27, 16, 2);

// VARIABLES
long duration;
float distance = -1;
int wastePercent = 0;

BlynkTimer timer;

// READ ULTRASONIC SENSOR
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  duration = pulseIn(ECHO_PIN, HIGH, 30000);

  if (duration == 0) {
    return -1;
  }

  return duration * 0.0343 / 2.0;
}

// EXISTING WASTE MONITORING
void checkWasteLevel() {
  distance = getDistance();

  if (distance < 0) {
    Serial.println("Ultrasonic sensor: No reading");

    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Sensor Error");

    return;
  }

  wastePercent =
    (int)(((EMPTY_DISTANCE - distance) /
    (EMPTY_DISTANCE - FULL_DISTANCE)) * 100.0);

  wastePercent = constrain(wastePercent, 0, 100);

  Serial.print("Distance: ");
  Serial.print(distance);
  Serial.print(" cm | Waste: ");
  Serial.print(wastePercent);
  Serial.println("%");

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Waste: ");
  lcd.print(wastePercent);
  lcd.print("%");

  lcd.setCursor(0, 1);

  if (wastePercent >= 90) {
    lcd.print("Status: FULL");
    digitalWrite(LED_PIN, HIGH);
  }
  else if (wastePercent >= 50) {
    lcd.print("Status: HALF");
    digitalWrite(LED_PIN, LOW);
  }
  else {
    lcd.print("Status: LOW");
    digitalWrite(LED_PIN, LOW);
  }

  // EXISTING BLYNK GAUGE
  if (Blynk.connected()) {
    Blynk.virtualWrite(V0, wastePercent);
  }
}

// NEW: SEND READING TO FASTAPI
void sendToFastAPI() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("FastAPI: WiFi disconnected");
    return;
  }

  if (distance < 0 || distance > EMPTY_DISTANCE) {
    Serial.println("FastAPI: Invalid distance, skipped");
    return;
  }

  WiFiClient client;
  HTTPClient http;

  http.setTimeout(1500);

  if (!http.begin(client, API_URL)) {
    Serial.println("FastAPI: Cannot start HTTP");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);

  String payload =
    "{\"device_id\":" + String(DEVICE_ID) +
    ",\"raw_distance_cm\":" + String(distance, 2) +
    "}";

  int httpCode = http.POST(payload);

  Serial.print("FastAPI HTTP Status: ");
  Serial.println(httpCode);

  if (httpCode > 0) {
    Serial.println(http.getString());
  } else {
    Serial.println(http.errorToString(httpCode));
  }

  http.end();
}

// SETUP
void setup() {
  Serial.begin(115200);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Wire.begin(SDA_PIN, SCL_PIN);

  lcd.init();
  lcd.backlight();

  lcd.setCursor(0, 0);
  lcd.print("Smart Waste Bin");

  lcd.setCursor(0, 1);
  lcd.print("Starting...");

  Blynk.begin(BLYNK_AUTH_TOKEN, ssid, pass);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Blynk Connected");
  delay(1500);

  // LOCAL MONITORING EVERY SECOND
  timer.setInterval(1000L, checkWasteLevel);

  // FASTAPI REPORTING EVERY 5 SECONDS
  timer.setInterval(5000L, sendToFastAPI);
}

// LOOP
void loop() {
  Blynk.run();
  timer.run();
}
