#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Int32MultiArray
import RPi.GPIO as GPIO

class MotorNode(Node):
    """ROS2 нод для управления моторами"""
    
    def __init__(self):
        super().__init__('motor_node')
        
        # Параметры
        self.declare_parameter('left_motor_pins', [17, 16])
        self.declare_parameter('right_motor_pins', [15, 14])
        self.declare_parameter('pwm_enabled', False)
        
        left_pins = self.get_parameter('left_motor_pins').value
        right_pins = self.get_parameter('right_motor_pins').value
        
        # Инициализация GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(left_pins + right_pins, GPIO.OUT)
        
        self.left_in1, self.left_in2 = left_pins
        self.right_in1, self.right_in2 = right_pins
        
        # Состояние моторов
        self.left_dir = 0
        self.right_dir = 0
        
        # Подписка на команды скорости
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10)
        
        # Публикация статуса
        self.status_pub = self.create_publisher(
            Int32MultiArray,
            'motor_status',
            10)
        
        # Таймер для публикации статуса
        self.create_timer(0.1, self.publish_status)
        
        self.get_logger().info('Motor node initialized')
        self.stop()
    
    def cmd_vel_callback(self, msg):
        """Обработка команд скорости"""
        linear = msg.linear.x
        angular = msg.angular.z
        
        self.get_logger().debug(f'Cmd: linear={linear:.2f}, angular={angular:.2f}')
        
        if abs(linear) < 0.1 and abs(angular) < 0.1:
            self.stop()
        elif angular > 0.1:
            self.turn_left()
        elif angular < -0.1:
            self.turn_right()
        elif linear > 0:
            self.forward()
        elif linear < 0:
            self.backward()
    
    def set_motor(self, motor, direction):
        """Установка направления мотора"""
        if motor == 'left':
            if direction == 1:
                GPIO.output(self.left_in1, GPIO.HIGH)
                GPIO.output(self.left_in2, GPIO.LOW)
                self.left_dir = 1
            elif direction == -1:
                GPIO.output(self.left_in1, GPIO.LOW)
                GPIO.output(self.left_in2, GPIO.HIGH)
                self.left_dir = -1
            else:
                GPIO.output([self.left_in1, self.left_in2], GPIO.LOW)
                self.left_dir = 0
        else:  # right
            if direction == 1:
                GPIO.output(self.right_in1, GPIO.HIGH)
                GPIO.output(self.right_in2, GPIO.LOW)
                self.right_dir = 1
            elif direction == -1:
                GPIO.output(self.right_in1, GPIO.LOW)
                GPIO.output(self.right_in2, GPIO.HIGH)
                self.right_dir = -1
            else:
                GPIO.output([self.right_in1, self.right_in2], GPIO.LOW)
                self.right_dir = 0
    
    def forward(self):
        self.set_motor('left', 1)
        self.set_motor('right', 1)
        self.get_logger().info('Forward')
    
    def backward(self):
        self.set_motor('left', -1)
        self.set_motor('right', -1)
        self.get_logger().info('Backward')
    
    def turn_left(self):
        self.set_motor('left', -1)
        self.set_motor('right', 1)
        self.get_logger().info('Turn left')
    
    def turn_right(self):
        self.set_motor('left', 1)
        self.set_motor('right', -1)
        self.get_logger().info('Turn right')
    
    def stop(self):
        self.set_motor('left', 0)
        self.set_motor('right', 0)
        self.get_logger().info('Stop')
    
    def publish_status(self):
        """Публикация статуса моторов"""
        msg = Int32MultiArray()
        msg.data = [self.left_dir, self.right_dir]
        self.status_pub.publish(msg)
    
    def destroy_node(self):
        self.stop()
        GPIO.cleanup()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MotorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()