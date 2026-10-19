
#include <Servo.h>

// ==========================================
// SMART WASTE BIN - AUTOMATIC LID
// Arduino UNO
// ==========================================

// PIN CONFIGURATION
#define TRIG_PIN 9
#define ECHO_PIN 10
#define SERVO_PIN 6
#define GREEN_LED 13

// SETTINGS
const float DETECTION_DISTANCE = 12.7; // 5 inches in cm

const int CLOSED_ANGLE = 0;
const int OPEN_ANGLE = 120;

const unsigned long HOLD_TIME = 5000; // 5 seconds
const unsigned long SENSOR_INTERVAL = 60;

// SERVO OBJECT
Servo lidServo;

// VARIABLES
bool lidOpen = false;
unsigned long lastHandDetected = 0;
unsigned long lastSensorRead = 0;

// ==========================================
// SETUP
// ==========================================
void setup() {
  Serial.begin(9600);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(GREEN_LED, OUTPUT);

  digitalWrite(TRIG_PIN, LOW);
  digitalWrite(GREEN_LED, LOW);

  lidServo.attach(SERVO_PIN);
  lidServo.write(CLOSED_ANGLE);

  Serial.println("Smart Waste Bin Starting...");
  delay(1000);
  Serial.println("System Ready!");
}

// ==========================================
// MEASURE DISTANCE
// ==========================================
float getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);

  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  unsigned long duration =
    pulseIn(ECHO_PIN, HIGH, 25000UL);

  // No valid echo
  if (duration == 0) {
    return -1;
  }

  float distance = duration * 0.0343 / 2.0;

  return distance;
}

// ==========================================
// OPEN LID
// ==========================================
void openLid() {
  lidServo.write(OPEN_ANGLE);
  digitalWrite(GREEN_LED, HIGH);

  lidOpen = true;

  Serial.println("Hand Detected!");
  Serial.println("Lid OPEN - Green LED ON");
}

// ==========================================
// CLOSE LID
// ==========================================
void closeLid() {
  lidServo.write(CLOSED_ANGLE);
  digitalWrite(GREEN_LED, LOW);

  lidOpen = false;

  Serial.println("Lid CLOSED - Green LED OFF");
}

// ==========================================
// MAIN LOOP
// ==========================================
void loop() {
  unsigned long currentTime = millis();

  // Read ultrasonic sensor every 60ms
  if (currentTime - lastSensorRead >= SENSOR_INTERVAL) {
    lastSensorRead = currentTime;

    float distance = getDistance();

    if (distance > 0 &&
        distance <= DETECTION_DISTANCE) {

      // Reset timer whenever hand is detected
      lastHandDetected = millis();

      if (!lidOpen) {
        openLid();
      }
    }

    // Print valid distance
    if (distance > 0) {
      Serial.print("Distance: ");
      Serial.print(distance);
      Serial.println(" cm");
    }
  }

  // Close lid 5 seconds after last detection
  if (lidOpen &&
      millis() - lastHandDetected >= HOLD_TIME) {
    closeLid();
  }
}
