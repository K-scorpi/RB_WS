#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray, Float32MultiArray, String
from my_robot.display.display_controller import DisplayController
import time

class DisplayNode(Node):
    """ROS2 нод для управления дисплеем"""
    
    def __init__(self):
        super().__init__('display_node')
        
        # Параметры
        self.declare_parameter('rotation', 90)
        self.declare_parameter('update_rate', 5.0)  # Гц
        
        rotation = self.get_parameter('rotation').value
        update_rate = self.get_parameter('update_rate').value
        
        # Инициализация дисплея
        self.display = DisplayController(rotation=rotation)
        
        # Состояние робота
        self.motor_left = 0
        self.motor_right = 0
        self.servo_pan = 90.0   # поворот (по умолчанию центр)
        self.servo_tilt = 90.0   # наклон (по умолчанию центр)
        self.camera_status = "OFF"
        
        # Подписка на статус моторов
        self.motor_sub = self.create_subscription(
            Int32MultiArray,
            'motor_status',
            self.motor_status_callback,
            10)
        
        # Подписка на статус сервоприводов
        self.servo_sub = self.create_subscription(
            Float32MultiArray,
            'servo/status',
            self.servo_status_callback,
            10)
        
        self.camera_sub = self.create_subscription(
            String,
            'camera/status',
            self.camera_callback,
            10)
        
        # Таймер для обновления дисплея
        self.create_timer(1.0/update_rate, self.update_display)
        
        self.get_logger().info('Display node initialized')
        
        # Показываем заставку
        self.show_splash()
        time.sleep(2)
    
    def motor_status_callback(self, msg):
        """Обновление статуса моторов"""
        if len(msg.data) >= 2:
            self.motor_left = msg.data[0]
            self.motor_right = msg.data[1]
    
    def servo_status_callback(self, msg):
        """Обновление статуса сервоприводов"""
        if len(msg.data) >= 2:
            self.servo_pan = msg.data[0]      # поворот
            self.servo_tilt = msg.data[1]      # наклон
    
    def direction_to_arrow(self, direction):
        """Преобразует направление мотора в стрелку"""
        if direction == 1:
            return "▲"
        elif direction == -1:
            return "▼"
        else:
            return "■"
    
    def get_servo_indicator(self, angle, min_angle=0, max_angle=180):
        """Создает графический индикатор положения сервопривода"""
        # Нормализуем угол от 0 до 1
        normalized = (angle - min_angle) / (max_angle - min_angle)
        if normalized < 0:
            normalized = 0
        elif normalized > 1:
            normalized = 1
        
        # Создаем полоску из 10 символов
        total_bars = 10
        filled = int(normalized * total_bars)
        empty = total_bars - filled
        
        return "█" * filled + "░" * empty
    
    def camera_callback(self, msg):
        """Обновление статуса камеры"""
        self.camera_status = msg.data
        self.get_logger().debug(f'Camera status: {self.camera_status}')
    
    def show_splash(self):
        """Показать заставку"""
        self.display.draw.rectangle((0, 0, self.display.width, self.display.height), fill=(0, 0, 50))
        self.display.draw.text((10, 30), "ROBOT", fill=(0, 255, 0), font=self.display.font_large)
        self.display.draw.text((10, 60), "CONTROL", fill=(0, 255, 0), font=self.display.font_large)
        self.display.draw.text((10, 100), "v2.0", fill=(255, 255, 255), font=self.display.font_medium)
        self.display.draw.text((10, 130), "with SERVOS", fill=(255, 255, 0), font=self.display.font_medium)
        self.display.display_image()
    
    def update_display(self):
        """Обновление информации на дисплее"""
        # Очистка
        self.display.draw.rectangle((0, 0, self.display.width, self.display.height), fill=(0, 0, 0))
        
        # Рамка
        self.display.draw.rectangle((2, 2, self.display.width-2, self.display.height-2), outline=(0, 100, 0))
        
        # Заголовок
        self.display.draw.text((10, 5), "ROBOT STATUS", fill=(0, 255, 0), font=self.display.font_medium)
        
        # Разделитель
        self.display.draw.line([(5, 35), (self.display.width-5, 35)], fill=(100, 100, 100))
        
        # ===== МОТОРЫ =====
        y = 40
        self.display.draw.text((10, y), "MOTORS:", fill=(255, 255, 0), font=self.display.font_small)
        
        # Левая гусеница
        y += 15
        left_arrow = self.direction_to_arrow(self.motor_left)
        self.display.draw.text((20, y), f"L: {left_arrow}", fill=(0, 255, 0), font=self.display.font_medium)
        
        # Правая гусеница
        self.display.draw.text((120, y), f"R: {self.direction_to_arrow(self.motor_right)}", 
                              fill=(0, 255, 0), font=self.display.font_medium)
        
        # ===== СЕРВОПРИВОДЫ =====
        y += 30
        self.display.draw.text((10, y), "SERVOS:", fill=(255, 255, 0), font=self.display.font_small)
        
        # Pan (поворот)
        y += 15
        self.display.draw.text((20, y), "Pan:", fill=(100, 255, 100), font=self.display.font_small)
        pan_indicator = self.get_servo_indicator(self.servo_pan)
        self.display.draw.text((70, y), f"{pan_indicator}", fill=(255, 255, 255), font=self.display.font_small)
        self.display.draw.text((180, y), f"{self.servo_pan:.0f}°", fill=(200, 200, 200), font=self.display.font_small)
        
        # Tilt (наклон)
        y += 15
        self.display.draw.text((20, y), "Tilt:", fill=(100, 255, 100), font=self.display.font_small)
        tilt_indicator = self.get_servo_indicator(self.servo_tilt)
        self.display.draw.text((70, y), f"{tilt_indicator}", fill=(255, 255, 255), font=self.display.font_small)
        self.display.draw.text((180, y), f"{self.servo_tilt:.0f}°", fill=(200, 200, 200), font=self.display.font_small)
        
        # ===== ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ =====
        y += 25
        
        # Время
        current_time = time.strftime("%H:%M:%S")
        self.display.draw.text((10, self.display.height-20), current_time, 
                              fill=(100, 100, 255), font=self.display.font_small)
        
        # Статус
        status_text = "ACTIVE" if (self.motor_left != 0 or self.motor_right != 0) else "IDLE"
        self.display.draw.text((self.display.width-80, self.display.height-20), status_text,
                              fill=(0, 255, 0) if status_text == "ACTIVE" else (100, 100, 100), 
                              font=self.display.font_small)
        
        camera_text = f"📷 {self.camera_status}"
        camera_color = (0, 255, 0) if "ACTIVE" in self.camera_status else (100, 100, 100)
        self.display.draw.text((10, self.display.height-40), camera_text,
                          fill=camera_color, font=self.display.font_small)
        
        # Отображаем
        self.display.display_image()
    
    def destroy_node(self):
        self.display.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = DisplayNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()