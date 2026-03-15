# 🤖 RB_WS - ROS2 Robot on Tracks

Гусеничный робот на Raspberry Pi 4B с управлением через ROS2 (Jazzy).

## 📦 Аппаратное обеспечение
- Raspberry Pi 4B (Ubuntu 24.04)
- Драйвер моторов L298N
- Дисплей WaveShare ST7789 (SPI)
- 2x сервопривода SG90 (Pan/Tilt для камеры)
- Камера OV5647 (CSI)
- Датчик расстояния HC-SR04 (в процессе)

## 🧩 ROS2 пакеты

### 1. my_robot (основной пакет)
- `motor_node` - управление моторами через L298N
  - Пины: IN1=17, IN2=16 (левый), IN3=15, IN4=14 (правый)
  - Топики: `/cmd_vel` (вход), `/motor_status` (выход)
  
- `servo_node` - управление сервоприводами SG90
  - Pan: GPIO5 (pin 29), Tilt: GPIO6 (pin 31)
  - Калибровка: Pan 2.5-12%, Tilt 2.5-8%
  - Топики: `/servo/pan`, `/servo/tilt`, `/servo/status`
  
- `display_node` - вывод статуса на дисплей ST7789
  - Поворот 90°, разрешение 320x170
  - Отображает: состояние моторов, углы серво, статус камеры
  
- `web_interface_node` - веб-управление
  - Flask + Socket.IO
  - MJPG стрим с камеры
  - Порт: 5000

### 2. robot_camera (пакет камеры)
- `rpicam_node` - захват видео через rpicam
  - Поддержка поворота 180°
  - Публикация в `/camera/image_raw`
  - Статус в `/camera/status`

## 🚀 Быстрый старт

```bash
# Клонирование
git clone https://github.com/K-scorpi/RB_WS.git
cd RB_WS

# Сборка
colcon build --symlink-install
source install/setup.bash

# Запуск всего робота
sudo -E ros2 launch my_robot robot_launch.py use_camera:=true

# Отдельные компоненты:
ros2 run my_robot motor_node
ros2 run my_robot servo_node
ros2 run my_robot display_node
ros2 run robot_camera rpicam_node
