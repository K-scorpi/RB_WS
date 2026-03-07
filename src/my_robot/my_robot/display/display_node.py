#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray, String
from my_robot.display.display_controller import DisplayController

class DisplayNode(Node):
    """ROS2 нод для управления дисплеем"""
    
    def __init__(self):
        super().__init__('display_node')
        
        # Параметры
        self.declare_parameter('rotation', 90)
        
        # Инициализация дисплея
        self.display = DisplayController(
            rotation=self.get_parameter('rotation').value
        )
        
        # Подписка на статус моторов
        self.motor_sub = self.create_subscription(
            Int32MultiArray,
            'motor_status',
            self.motor_status_callback,
            10)
        
        # Подписка на сообщения для дисплея
        self.display_sub = self.create_subscription(
            String,
            'display_message',
            self.display_callback,
            10)
        
        # Таймер для обновления времени
        self.create_timer(1.0, self.update_time)
        
        self.get_logger().info('Display node initialized')
        
        # Показываем заставку
        self.display.show_splash()
    
    def motor_status_callback(self, msg):
        """Обновление статуса моторов на дисплее"""
        if len(msg.data) >= 2:
            self.display.show_robot_status(msg.data[0], msg.data[1])
    
    def display_callback(self, msg):
        """Отображение произвольного сообщения"""
        self.display.show_text(msg.data, 10, 10)
    
    def update_time(self):
        """Обновление времени на дисплее (если нужно)"""
        pass
    
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