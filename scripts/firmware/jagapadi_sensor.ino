// Jagapadi field sensor: ESP32 + capacitive soil-moisture probe + ultrasonic water-level sensor.
// Sends one reading every 30 minutes to POST /api/sensors/<FIELD_ID>.
// Calibrate SOIL_DRY / SOIL_WET with the probe in air and in saturated soil before use.
#include <WiFi.h>
#include <HTTPClient.h>

const char* WIFI_SSID = "your-wifi";
const char* WIFI_PASS = "your-password";
const char* API = "https://your-jagapadi-host/api/sensors/FIELD01";
const char* TOKEN = "token-from-backend-config";  // backend/config/sensor_tokens.json: {"FIELD01": "..."}

const int SOIL_PIN = 34, TRIG_PIN = 5, ECHO_PIN = 18;
const int SOIL_DRY = 3200, SOIL_WET = 1300;   // raw ADC readings
const float SENSOR_HEIGHT_MM = 600;           // sensor height above the paddy soil surface

float soilMoisture() {
  int raw = analogRead(SOIL_PIN);
  float f = (float)(SOIL_DRY - raw) / (SOIL_DRY - SOIL_WET);
  return constrain(f, 0.0, 1.0) * 0.45;       // map to volumetric water content, saturated paddy ~0.45 m3/m3
}

float waterLevelMm() {
  digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long us = pulseIn(ECHO_PIN, HIGH, 30000);
  if (us == 0) return NAN;
  return SENSOR_HEIGHT_MM - us * 0.343 / 2.0;  // positive = water above the soil
}

void setup() {
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(500);
  if (WiFi.status() == WL_CONNECTED) {
    float level = waterLevelMm();
    String body = String("{\"token\":\"") + TOKEN + "\",\"soil_moisture_m3m3\":" + String(soilMoisture(), 3);
    if (!isnan(level)) body += ",\"water_level_mm\":" + String(level, 0);
    body += "}";
    HTTPClient http;
    http.begin(API);
    http.addHeader("Content-Type", "application/json");
    http.POST(body);
    http.end();
  }
  esp_sleep_enable_timer_wakeup(30ULL * 60 * 1000000);  // 30 minutes
  esp_deep_sleep_start();
}

void loop() {}
