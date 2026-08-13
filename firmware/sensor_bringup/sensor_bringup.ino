// Swing Monitor — Sensor Bring-up
//
// Reads raw accelerometer + gyroscope and fused orientation (quaternion)
// from the BNO085 over I2C, and reports the achieved sample rate so it
// can be checked against the 100Hz+ target needed to resolve a swing.
//
// Board:   Arduino Nano ESP32
// Sensor:  Adafruit BNO085 9-DOF (STEMMA QT / Qwiic)
// Library: Adafruit BNO08x (install via Library Manager, plus Adafruit BusIO)
//
// Wiring: connect via the Nano ESP32's onboard Qwiic connector, or SDA/SCL
// if wired directly. BNO08X_RESET/BNO08X_INT are optional — set to a GPIO
// number if wired, or leave as -1 if not connected.

#include <Adafruit_BNO08x.h>

#define BNO08X_RESET -1
#define BNO08X_INT   -1

Adafruit_BNO08x bno08x(BNO08X_RESET);
sh2_SensorValue_t sensorValue;

// Target report interval in microseconds (5000us = 200Hz, comfortably above
// the 100Hz+ target so the sensor isn't the bottleneck).
const uint32_t REPORT_INTERVAL_US = 5000;

uint32_t accelCount = 0;
uint32_t gyroCount = 0;
uint32_t rotationCount = 0;
uint32_t rateWindowStart = 0;

// Latest values, updated every sample but only printed once per second —
// printing on every sample was slow enough to throttle the read loop and
// undercount the true achievable sample rate.
float lastAccelX, lastAccelY, lastAccelZ;
float lastGyroX, lastGyroY, lastGyroZ;
float lastQuatI, lastQuatJ, lastQuatK, lastQuatReal;

void setReports() {
  Serial.println("Enabling accelerometer, gyroscope, and rotation vector reports...");

  if (!bno08x.enableReport(SH2_ACCELEROMETER, REPORT_INTERVAL_US)) {
    Serial.println("Could not enable accelerometer");
  }
  if (!bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED, REPORT_INTERVAL_US)) {
    Serial.println("Could not enable gyroscope");
  }
  if (!bno08x.enableReport(SH2_ROTATION_VECTOR, REPORT_INTERVAL_US)) {
    Serial.println("Could not enable rotation vector");
  }
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  Serial.println("Swing Monitor - Sensor Bring-up");

  if (!bno08x.begin_I2C()) {
    Serial.println("Failed to find BNO085 - check wiring");
    while (1) {
      delay(10);
    }
  }
  Serial.println("BNO085 found");

  setReports();

  rateWindowStart = millis();
}

void loop() {
  if (bno08x.wasReset()) {
    Serial.println("Sensor was reset, re-enabling reports");
    setReports();
  }

  if (!bno08x.getSensorEvent(&sensorValue)) {
    return;
  }

  switch (sensorValue.sensorId) {
    case SH2_ACCELEROMETER:
      accelCount++;
      lastAccelX = sensorValue.un.accelerometer.x;
      lastAccelY = sensorValue.un.accelerometer.y;
      lastAccelZ = sensorValue.un.accelerometer.z;
      break;

    case SH2_GYROSCOPE_CALIBRATED:
      gyroCount++;
      lastGyroX = sensorValue.un.gyroscope.x;
      lastGyroY = sensorValue.un.gyroscope.y;
      lastGyroZ = sensorValue.un.gyroscope.z;
      break;

    case SH2_ROTATION_VECTOR:
      rotationCount++;
      lastQuatI = sensorValue.un.rotationVector.i;
      lastQuatJ = sensorValue.un.rotationVector.j;
      lastQuatK = sensorValue.un.rotationVector.k;
      lastQuatReal = sensorValue.un.rotationVector.real;
      break;
  }

  // Report each report type's achieved sample rate once per second, so it
  // can be checked against the 100Hz+ target from the project plan. This is
  // also the only place we print, so the read loop isn't throttled by the
  // cost of Serial output.
  uint32_t now = millis();
  uint32_t elapsed = now - rateWindowStart;
  if (elapsed >= 1000) {
    Serial.print(">>> Sample rates (Hz) - Accel: ");
    Serial.print(accelCount * 1000.0f / elapsed, 1);
    Serial.print(", Gyro: ");
    Serial.print(gyroCount * 1000.0f / elapsed, 1);
    Serial.print(", Rotation: ");
    Serial.println(rotationCount * 1000.0f / elapsed, 1);

    Serial.print("    Latest Accel (m/s^2): ");
    Serial.print(lastAccelX, 3);
    Serial.print(", ");
    Serial.print(lastAccelY, 3);
    Serial.print(", ");
    Serial.println(lastAccelZ, 3);

    Serial.print("    Latest Gyro (rad/s): ");
    Serial.print(lastGyroX, 3);
    Serial.print(", ");
    Serial.print(lastGyroY, 3);
    Serial.print(", ");
    Serial.println(lastGyroZ, 3);

    Serial.print("    Latest Quat (i,j,k,real): ");
    Serial.print(lastQuatI, 3);
    Serial.print(", ");
    Serial.print(lastQuatJ, 3);
    Serial.print(", ");
    Serial.print(lastQuatK, 3);
    Serial.print(", ");
    Serial.println(lastQuatReal, 3);

    accelCount = 0;
    gyroCount = 0;
    rotationCount = 0;
    rateWindowStart = now;
  }
}
