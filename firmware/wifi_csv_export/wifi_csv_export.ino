// Swing Monitor — Wireless CSV Export (WiFi)
//
// The board hosts its own WiFi hotspot (no router or existing network
// needed — works anywhere, e.g. a driving range) and streams accelerometer,
// gyroscope, and rotation vector (quaternion) readings as CSV rows over TCP
// to whichever laptop joins that hotspot.
//
// Setup:
// 1. Upload and power the board (USB or battery). It'll print its hotspot
//    SSID and IP address (normally 192.168.4.1) to Serial.
// 2. On your laptop, join the WiFi network below (you'll lose general
//    internet access while connected — expected, the board isn't routing
//    to the internet).
// 3. Start capturing to a file:
//        nc 192.168.4.1 5005 > swing_data.csv
// 4. When done, Ctrl+C the `nc` command to close the file.
//
// CSV columns: millis,type,x,y,z,w  (w only populated for QUAT rows)

#include <Wire.h>
#include <WiFi.h>
#include <Adafruit_BNO08x.h>

const char* AP_SSID = "swing-monitor";
const char* AP_PASSWORD = "swingmonitor123";  // WPA2 requires 8+ characters
const uint16_t SERVER_PORT = 5005;

#define BNO08X_RESET -1

Adafruit_BNO08x bno08x(BNO08X_RESET);
sh2_SensorValue_t sensorValue;
WiFiServer server(SERVER_PORT);
WiFiClient client;

// 200Hz — comfortably above the 100Hz+ target.
const uint32_t REPORT_INTERVAL_US = 5000;

void setReports() {
  bno08x.enableReport(SH2_ACCELEROMETER, REPORT_INTERVAL_US);
  bno08x.enableReport(SH2_GYROSCOPE_CALIBRATED, REPORT_INTERVAL_US);
  bno08x.enableReport(SH2_ROTATION_VECTOR, REPORT_INTERVAL_US);
}

void startAccessPoint() {
  WiFi.softAP(AP_SSID, AP_PASSWORD);
  Serial.print("Hotspot \"");
  Serial.print(AP_SSID);
  Serial.print("\" up, IP: ");
  Serial.println(WiFi.softAPIP());
  server.begin();
}

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }

  startAccessPoint();

  if (!bno08x.begin_I2C()) {
    Serial.println("Failed to find BNO085 - check wiring");
    while (1) {
      delay(10);
    }
  }

  // Bump from the 100kHz default to 400kHz (I2C fast mode) — set after
  // begin_I2C() so the library's own Wire.begin() doesn't reset it back.
  Wire.setClock(400000);

  setReports();

  Serial.println("Waiting for laptop to connect...");
}

void sendRow(uint32_t t, const char* type, float x, float y, float z, float w, bool hasW) {
  // Build the whole row and send it as a single write — sending each field
  // as a separate client.print() call was six TCP writes per sample, which
  // over WiFi was slow enough to throttle the achievable sample rate well
  // below the sensor's actual output rate.
  char buf[96];
  int len;
  if (hasW) {
    len = snprintf(buf, sizeof(buf), "%lu,%s,%.4f,%.4f,%.4f,%.4f\n", t, type, x, y, z, w);
  } else {
    len = snprintf(buf, sizeof(buf), "%lu,%s,%.4f,%.4f,%.4f,\n", t, type, x, y, z);
  }
  client.write((const uint8_t*)buf, len);
}

void loop() {
  if (bno08x.wasReset()) {
    setReports();
  }

  if (!client.connected()) {
    client = server.available();
    if (client) {
      client.setNoDelay(true);  // don't let TCP delay small writes waiting to batch
      Serial.println("Laptop connected - streaming CSV");
      client.println("millis,type,x,y,z,w");
    }
    return;
  }

  if (!bno08x.getSensorEvent(&sensorValue)) {
    return;
  }

  uint32_t t = millis();

  switch (sensorValue.sensorId) {
    case SH2_ACCELEROMETER:
      sendRow(t, "ACCEL", sensorValue.un.accelerometer.x,
              sensorValue.un.accelerometer.y, sensorValue.un.accelerometer.z,
              0, false);
      break;

    case SH2_GYROSCOPE_CALIBRATED:
      sendRow(t, "GYRO", sensorValue.un.gyroscope.x,
              sensorValue.un.gyroscope.y, sensorValue.un.gyroscope.z, 0,
              false);
      break;

    case SH2_ROTATION_VECTOR:
      sendRow(t, "QUAT", sensorValue.un.rotationVector.i,
              sensorValue.un.rotationVector.j, sensorValue.un.rotationVector.k,
              sensorValue.un.rotationVector.real, true);
      break;
  }
}
