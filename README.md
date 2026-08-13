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

