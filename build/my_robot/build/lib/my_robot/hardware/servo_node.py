#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Float32MultiArray
import RPi.GPIO as GPIO
import time
import threading

class ServoNode(Node):
    """ROS2 нод для управления двумя сервоприводами SG90"""
    
    def __init__(self):
        super().__init__('servo_node')
        
        # Параметры с твоими калибровочными значениями
        self.declare_parameter('pan_pin', 5)    # BCM 5 = pin 29 для поворота
        self.declare_parameter('tilt_pin', 6)   # BCM 6 = pin 31 для наклона
        self.declare_parameter('pan_min_duty', 2.5)   # Левый край
        self.declare_parameter('pan_max_duty', 12.0)  # Правый край
        self.declare_parameter('tilt_min_duty', 2.5)  # Верхний край
        self.declare_parameter('tilt_max_duty', 8.0)  # Нижний край
        self.declare_parameter('freq', 50)             # 50 Гц для SG90
        
        pan_pin = self.get_parameter('pan_pin').value
        tilt_pin = self.get_parameter('tilt_pin').value
        self.pan_min_duty = self.get_parameter('pan_min_duty').value
        self.pan_max_duty = self.get_parameter('pan_max_duty').value
        self.tilt_min_duty = self.get_parameter('tilt_min_duty').value
        self.tilt_max_duty = self.get_parameter('tilt_max_duty').value
        freq = self.get_parameter('freq').value
        
        # Ограничения углов (0-180)
        self.pan_min_angle = 0
        self.pan_max_angle = 180
        self.tilt_min_angle = 0
        self.tilt_max_angle = 180
        
        self.get_logger().info(f'Инициализация сервоприводов:')
        self.get_logger().info(f'  Pan (поворот) - BCM {pan_pin} (pin 29)')
        self.get_logger().info(f'    Duty: min={self.pan_min_duty}%, max={self.pan_max_duty}%')
        self.get_logger().info(f'  Tilt (наклон) - BCM {tilt_pin} (pin 31)')
        self.get_logger().info(f'    Duty: min={self.tilt_min_duty}%, max={self.tilt_max_duty}%')
        
        # Настройка GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([pan_pin, tilt_pin], GPIO.OUT)
        
        # Настройка PWM
        self.pan_servo = GPIO.PWM(pan_pin, freq)
        self.tilt_servo = GPIO.PWM(tilt_pin, freq)
        
        # Начальные положения (центр)
        self.pan_angle = 90.0
        self.tilt_angle = 90.0
        
        # Флаг для управления подавлением джиттера
        self.servo_active = False
        self.active_timer = None
        
        # Запуск PWM с начальными значениями
        pan_duty = self.angle_to_duty('pan', self.pan_angle)
        tilt_duty = self.angle_to_duty('tilt', self.tilt_angle)
        
        self.pan_servo.start(pan_duty)
        self.tilt_servo.start(tilt_duty)
        
        # Запускаем таймер для отключения сигнала (убираем джиттер)
        self.servo_active = True
        self.start_inactivity_timer()
        
        self.get_logger().info(f'Начальные углы: Pan={self.pan_angle}°, Tilt={self.tilt_angle}°')
        self.get_logger().info(f'Начальные duty: Pan={pan_duty:.2f}%, Tilt={tilt_duty:.2f}%')
        
        # Подписки на топики
        self.pan_sub = self.create_subscription(
            Float32,
            'servo/pan',
            self.pan_callback,
            10)
            
        self.tilt_sub = self.create_subscription(
            Float32,
            'servo/tilt',
            self.tilt_callback,
            10)
            
        self.both_sub = self.create_subscription(
            Float32MultiArray,
            'servo/both',
            self.both_callback,
            10)
        
        # Публикация статуса
        self.status_pub = self.create_publisher(
            Float32MultiArray,
            'servo/status',
            10)
        
        # Таймер для публикации статуса (каждые 500 мс)
        self.create_timer(0.5, self.publish_status)
        
        self.get_logger().info('✅ Servo node started')
        
    def angle_to_duty(self, servo, angle):
        """Конвертирует угол (0-180) в коэффициент заполнения ШИМ"""
        if servo == 'pan':
            min_duty = self.pan_min_duty
            max_duty = self.pan_max_duty
        else:  # tilt
            min_duty = self.tilt_min_duty
            max_duty = self.tilt_max_duty
        
        # Линейная интерполяция
        duty = min_duty + (angle / 180.0) * (max_duty - min_duty)
        return duty
    
    def duty_to_angle(self, servo, duty):
        """Конвертирует duty cycle обратно в угол"""
        if servo == 'pan':
            min_duty = self.pan_min_duty
            max_duty = self.pan_max_duty
        else:
            min_duty = self.tilt_min_duty
            max_duty = self.tilt_max_duty
        
        angle = ((duty - min_duty) / (max_duty - min_duty)) * 180.0
        return max(0, min(180, angle))
    
    def set_servo_angle(self, servo, angle):
        """Устанавливает угол сервопривода"""
        # Проверяем диапазон
        if angle < 0:
            angle = 0
            self.get_logger().warn('Угол скорректирован до 0°')
        elif angle > 180:
            angle = 180
            self.get_logger().warn('Угол скорректирован до 180°')
        
        duty = self.angle_to_duty(servo, angle)
        
        # Включаем сигнал
        if servo == 'pan':
            self.pan_servo.ChangeDutyCycle(duty)
            self.pan_angle = angle
            self.get_logger().info(f'✅ Pan (поворот): {angle:.1f}° (duty={duty:.2f}%)')
        elif servo == 'tilt':
            self.tilt_servo.ChangeDutyCycle(duty)
            self.tilt_angle = angle
            self.get_logger().info(f'✅ Tilt (наклон): {angle:.1f}° (duty={duty:.2f}%)')
        
        # Сбрасываем таймер неактивности
        self.servo_active = True
        self.start_inactivity_timer()
    
    def start_inactivity_timer(self):
        """Запускает таймер для отключения сигнала"""
        # Отменяем предыдущий таймер если был
        if self.active_timer:
            self.active_timer.cancel()
        
        # Создаем новый таймер на 0.5 секунды
        self.active_timer = threading.Timer(0.5, self.disable_servo_signal)
        self.active_timer.daemon = True
        self.active_timer.start()
    
    def disable_servo_signal(self):
        """Отключает сигнал на сервоприводах для предотвращения джиттера"""
        if self.servo_active:
            self.get_logger().debug('Отключение сигнала сервоприводов')
            self.pan_servo.ChangeDutyCycle(0)
            self.tilt_servo.ChangeDutyCycle(0)
            self.servo_active = False
    
    def pan_callback(self, msg):
        """Обработка команд для поворота"""
        self.get_logger().info(f'📥 Получена команда pan: {msg.data}°')
        self.set_servo_angle('pan', msg.data)
    
    def tilt_callback(self, msg):
        """Обработка команд для наклона"""
        self.get_logger().info(f'📥 Получена команда tilt: {msg.data}°')
        self.set_servo_angle('tilt', msg.data)
    
    def both_callback(self, msg):
        """Обработка команд для обоих сервоприводов одновременно"""
        if len(msg.data) >= 2:
            self.get_logger().info(f'📥 Получена команда both: pan={msg.data[0]}°, tilt={msg.data[1]}°')
            self.set_servo_angle('pan', msg.data[0])
            self.set_servo_angle('tilt', msg.data[1])
    
    def publish_status(self):
        """Публикация текущих углов"""
        msg = Float32MultiArray()
        msg.data = [self.pan_angle, self.tilt_angle]
        self.status_pub.publish(msg)
        self.get_logger().debug(f'📊 Статус: Pan={self.pan_angle}°, Tilt={self.tilt_angle}°')
    
    def destroy_node(self):
        """Очистка при завершении"""
        self.get_logger().info('🛑 Остановка сервоприводов...')
        if self.active_timer:
            self.active_timer.cancel()
        self.pan_servo.stop()
        self.tilt_servo.stop()
        GPIO.cleanup()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ServoNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()