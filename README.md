# Swing Monitor

Arduino sensor project for golf. Mounted IMU sensor on the club shaft allows for live measuring (and transfer of data over IoT/BLE in real time for display) of per-swing metrics, all derived from the shaft-mounted IMU's accelerometer, gyroscope, and fused orientation output.

## Key Metrics

**Speed**
* Peak clubhead speed
* Clubhead speed at impact

**Timing**
* Backswing time (address → top)
* Downswing time (top → impact)
* Tempo ratio (backswing:downswing)
* Total swing time

**Plane**
* Swing plane angle
* Plane angle delta (top of backswing vs. impact)

**Rotational / release**
* Peak angular velocity (wrist/face rotation rate)
* Timing of peak angular velocity relative to impact (early = casting, late = lag/release)

**Impact**
* Peak acceleration spike at impact (magnitude and sharpness)
* Angle of attack at impact (steep vs. shallow) — noisier, since it depends on precise impact detection from the accelerometer alone

## Hardware

* [Ardunio Nano ESP32](https://thepihut.com/products/arduino-nano-esp32-with-headers)
* [Adafruit 9-DOF Orentiation IMU Fusion Breakout - BNO085](https://thepihut.com/products/adafruit-9-dof-orientation-imu-fusion-breakout-bno085-bno080-stemma-qt-qwiic)
* LiPo 3.7v Battery
* 3D printed casing

## Project Plan

1. **Hardware assembly** — wire BNO085 to Nano ESP32 (I2C/Qwiic), confirm power draw against LiPo capacity, mount in 3D printed casing on shaft
2. **Sensor bring-up** — read raw accelerometer/gyroscope and fused orientation (quaternion) output from the BNO085, verify sample rate is sufficient to capture a swing (target 100Hz+) — see [`firmware/sensor_bringup`](firmware/sensor_bringup/sensor_bringup.ino)
3. **Swing event detection** — segment a continuous data stream into address, top of backswing, impact, and finish
4. **Metric calculation** — compute per-swing metrics (speed, timing, plane, rotational/release, impact) from segmented data
5. **Calibration & validation** — sanity-check computed metrics against known reference values (e.g. compare clubhead speed estimates to a radar/launch monitor) and tune impact/event detection thresholds
6. **Data transfer** — stream metrics over BLE from the Nano ESP32
7. **Display** — companion app or device to receive and display metrics in real time
8. **Enclosure refinement** — iterate on 3D printed casing for secure, low-profile shaft mounting

