#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import cv2
import numpy as np
import base64
import json
import time

class WebInterfaceNode(Node):
    """ROS2 нод для веб-интерфейса робота"""
    
    def __init__(self):
        super().__init__('web_interface_node')
        
        self.get_logger().info('Запуск веб-интерфейса...')
        
        # Bridge для конвертации изображений
        self.bridge = CvBridge()
        
        # Состояние робота
        self.robot_status = {
            'motors': {'left': 0, 'right': 0},
            'servos': {'pan': 90.0, 'tilt': 90.0},
            'camera': 'OFF',
            'battery': 100.0,
            'mode': 'manual'
        }
        
        # Последний кадр с камеры
        self.last_frame = None
        self.frame_lock = threading.Lock()
        
        # Подписки
        self.motor_sub = self.create_subscription(
            Float32MultiArray,
            'motor_status',
            self.motor_callback,
            10)
        
        self.servo_sub = self.create_subscription(
            Float32MultiArray,
            'servo/status',
            self.servo_callback,
            10)
        
        self.camera_status_sub = self.create_subscription(
            String,
            'camera/status',
            self.camera_status_callback,
            10)
        
        self.camera_sub = self.create_subscription(
            Image,
            'camera/image_raw',
            self.camera_callback,
            10)
        
        # Публикаторы для управления
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.servo_pan_pub = self.create_publisher(Float32MultiArray, 'servo/both', 10)
        
        # Запуск Flask в отдельном потоке
        self.flask_thread = threading.Thread(target=self.run_flask)
        self.flask_thread.daemon = True
        self.flask_thread.start()
        
        self.get_logger().info('✅ Веб-интерфейс запущен на http://localhost:5000')
    
    def motor_callback(self, msg):
        if len(msg.data) >= 2:
            self.robot_status['motors']['left'] = msg.data[0]
            self.robot_status['motors']['right'] = msg.data[1]
    
    def servo_callback(self, msg):
        if len(msg.data) >= 2:
            self.robot_status['servos']['pan'] = msg.data[0]
            self.robot_status['servos']['tilt'] = msg.data[1]
    
    def camera_status_callback(self, msg):
        self.robot_status['camera'] = msg.data
    
    def camera_callback(self, msg):
    """Сохранение последнего кадра с камеры"""
    try:
        cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        with self.frame_lock:
            # Сжимаем JPEG для веба
            _, jpeg = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, 70])
            self.last_frame = jpeg.tobytes()
            self.get_logger().info('✅ Получен кадр с камеры', throttle_duration_sec=5.0)
    except Exception as e:
        self.get_logger().error(f'Ошибка обработки кадра: {e}')
    
    def run_flask(self):
        """Запуск Flask приложения"""
        app = Flask(__name__)
        socketio = SocketIO(app, cors_allowed_origins="*")
        
        @app.route('/')
        def index():
            return render_template('robot_control.html')
        
        @app.route('/video_feed')
        def video_feed():
            """MJPG стрим для видео"""
            def generate():
                while True:
                    with self.frame_lock:
                        if self.last_frame:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + self.last_frame + b'\r\n')
                    time.sleep(0.05)  # 20 fps
            
            return Response(generate(),
                          mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @app.route('/video_feed')
        def video_feed():
            """Простой JPEG стрим"""
            def generate():
                import cv2
                # Для теста создадим простое изображение если нет камеры
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(test_frame, "Camera Ready", (200, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                while True:
                    with self.frame_lock:
                        if self.last_frame:
                            # Если есть реальный кадр - используем его
                            frame_data = self.last_frame
                        else:
                            # Если нет - тестовое изображение
                            _, jpeg = cv2.imencode('.jpg', test_frame)
                            frame_data = jpeg.tobytes()
                    
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
                    time.sleep(0.1)  # 10 fps
            
            return Response(generate(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
        
        @socketio.on('command')
        def handle_command(data):
            """Обработка команд с веб-интерфейса"""
            cmd = data.get('command')
            value = data.get('value', 0)
            
            self.get_logger().info(f'Получена команда: {cmd}={value}')
            
            if cmd == 'forward':
                twist = Twist()
                twist.linear.x = 0.3
                self.cmd_vel_pub.publish(twist)
                
            elif cmd == 'backward':
                twist = Twist()
                twist.linear.x = -0.3
                self.cmd_vel_pub.publish(twist)
                
            elif cmd == 'left':
                twist = Twist()
                twist.angular.z = 0.5
                self.cmd_vel_pub.publish(twist)
                
            elif cmd == 'right':
                twist = Twist()
                twist.angular.z = -0.5
                self.cmd_vel_pub.publish(twist)
                
            elif cmd == 'stop':
                twist = Twist()
                self.cmd_vel_pub.publish(twist)
                
            elif cmd == 'servo_pan':
                msg = Float32MultiArray()
                msg.data = [value, self.robot_status['servos']['tilt']]
                self.servo_pan_pub.publish(msg)
                
            elif cmd == 'servo_tilt':
                msg = Float32MultiArray()
                msg.data = [self.robot_status['servos']['pan'], value]
                self.servo_pan_pub.publish(msg)
        
        @socketio.on('joystick')
        def handle_joystick(data):
            """Обработка джойстика"""
            x = data.get('x', 0)
            y = data.get('y', 0)
            
            twist = Twist()
            twist.linear.x = y * 0.5  # Вперед/назад
            twist.angular.z = -x * 0.5  # Поворот
            self.cmd_vel_pub.publish(twist)
        
        # Запуск сервера
        socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
    
    def destroy_node(self):
        self.get_logger().info('Остановка веб-интерфейса')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = WebInterfaceNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()