#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Float32MultiArray, Int32MultiArray
from geometry_msgs.msg import Twist
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit
import threading
import cv2
import numpy as np
import time
import socket
import json
import os

class UnifiedWebNode(Node):
    """Единая веб-панель управления роботом"""
    
    def __init__(self):
        super().__init__('unified_web_node')
        
        # Параметры
        self.declare_parameter('port', 5000)
        self.declare_parameter('video_port', 8080)
        self.port = self.get_parameter('port').value
        self.video_port = self.get_parameter('video_port').value
        
        self.get_logger().info('=' * 50)
        self.get_logger().info('🚀 ЗАПУСК ЕДИНОЙ ВЕБ-ПАНЕЛИ')
        self.get_logger().info('=' * 50)
        
        # Состояние робота
        self.robot_state = {
            'motors': {'left': 0, 'right': 0},
            'servos': {'pan': 90.0, 'tilt': 90.0},
            'camera': 'OFF',
            'clients': 0
        }
        self.state_lock = threading.Lock()
        
        # Для видео
        self.bridge = CvBridge()
        self.last_frame = None
        self.frame_lock = threading.Lock()
        
        # СОЗДАЕМ ПУБЛИКАТОРЫ (это было пропущено!)
        self.cmd_vel_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.servo_pub = self.create_publisher(Float32MultiArray, 'servo/both', 10)
        
        # Подписки на топики ROS
        self.motor_sub = self.create_subscription(
            Int32MultiArray,
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
        
        # Запуск Flask в отдельном потоке
        self.flask_thread = threading.Thread(target=self.run_flask)
        self.flask_thread.daemon = True
        self.flask_thread.start()
        
        self.get_logger().info(f'✅ Веб-панель на http://localhost:{self.port}')
        self.get_logger().info(f'✅ Публикаторы созданы:')
        self.get_logger().info(f'   - cmd_vel (управление моторами)')
        self.get_logger().info(f'   - servo/both (управление сервоприводами)')
        self.get_ip_address()
    
    def motor_callback(self, msg):
        """Обновление статуса моторов"""
        if len(msg.data) >= 2:
            with self.state_lock:
                self.robot_state['motors']['left'] = msg.data[0]
                self.robot_state['motors']['right'] = msg.data[1]
    
    def servo_callback(self, msg):
        """Обновление статуса сервоприводов"""
        if len(msg.data) >= 2:
            with self.state_lock:
                self.robot_state['servos']['pan'] = float(msg.data[0])
                self.robot_state['servos']['tilt'] = float(msg.data[1])
    
    def camera_status_callback(self, msg):
        """Обновление статуса камеры"""
        with self.state_lock:
            self.robot_state['camera'] = msg.data
    
    def camera_callback(self, msg):
        """Обработка видеокадров"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
            _, jpeg = cv2.imencode('.jpg', cv_image, [cv2.IMWRITE_JPEG_QUALITY, 60])
            with self.frame_lock:
                self.last_frame = jpeg.tobytes()
        except Exception as e:
            self.get_logger().error(f'Ошибка обработки видео: {e}')
    
    def get_ip_address(self):
        """Получение IP адреса"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            self.get_logger().info(f'📱 Доступно по IP: http://{ip}:{self.port}')
        except:
            pass
    
    def run_flask(self):
        """Запуск Flask приложения с Socket.IO"""
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'robot_secret_key'
        socketio = SocketIO(app, cors_allowed_origins="*", logger=False, engineio_logger=False)
        
        @app.route('/')
        def index():
            return render_template('unified_control.html', 
                                 video_port=self.video_port,
                                 host=request.host.split(':')[0])
        
        @app.route('/api/state')
        def get_state():
            """Получение текущего состояния"""
            with self.state_lock:
                return jsonify(self.robot_state)
        
        @socketio.on('connect')
        def handle_connect():
            """Обработка подключения клиента"""
            with self.state_lock:
                self.robot_state['clients'] += 1
            self.get_logger().info(f'👤 Клиент подключен. Всего: {self.robot_state["clients"]}')
        
        @socketio.on('disconnect')
        def handle_disconnect():
            """Обработка отключения клиента"""
            with self.state_lock:
                self.robot_state['clients'] -= 1
            self.get_logger().info(f'👤 Клиент отключен. Осталось: {self.robot_state["clients"]}')
        
        @socketio.on('command')
        def handle_command(data):
            """Обработка команд управления"""
            cmd = data.get('command')
            value = data.get('value', 0)
            
            # Добавим больше отладки
            self.get_logger().info(f'🎮 ПОЛУЧЕНА КОМАНДА: {cmd} = {value}')
            self.get_logger().info(f'📦 Данные команды: {data}')
            
            if cmd in ['forward', 'backward', 'left', 'right', 'stop']:
                twist = Twist()
                if cmd == 'forward':
                    twist.linear.x = 0.3
                    self.get_logger().info('➡️ ПУБЛИКАЦИЯ: ВПЕРЕД')
                elif cmd == 'backward':
                    twist.linear.x = -0.3
                    self.get_logger().info('⬅️ ПУБЛИКАЦИЯ: НАЗАД')
                elif cmd == 'left':
                    twist.angular.z = 0.5
                    self.get_logger().info('↪️ ПУБЛИКАЦИЯ: НАЛЕВО')
                elif cmd == 'right':
                    twist.angular.z = -0.5
                    self.get_logger().info('↩️ ПУБЛИКАЦИЯ: НАПРАВО')
                elif cmd == 'stop':
                    self.get_logger().info('⏹️ ПУБЛИКАЦИЯ: СТОП')
                
                self.cmd_vel_pub.publish(twist)
                self.get_logger().info('✅ Команда опубликована в /cmd_vel')
                
            elif cmd == 'servo_pan':
                msg = Float32MultiArray()
                with self.state_lock:
                    msg.data = [float(value), self.robot_state['servos']['tilt']]
                self.get_logger().info(f'🎯 ПУБЛИКАЦИЯ СЕРВО: Pan={value}°')
                self.servo_pub.publish(msg)
                
            elif cmd == 'servo_tilt':
                msg = Float32MultiArray()
                with self.state_lock:
                    msg.data = [self.robot_state['servos']['pan'], float(value)]
                self.get_logger().info(f'🎯 ПУБЛИКАЦИЯ СЕРВО: Tilt={value}°')
                self.servo_pub.publish(msg)
        
        @socketio.on('joystick')
        def handle_joystick(data):
            """Обработка джойстика"""
            x = data.get('x', 0)
            y = data.get('y', 0)
            
            twist = Twist()
            twist.linear.x = y * 0.5
            twist.angular.z = -x * 0.5
            self.get_logger().info(f'🕹️ Джойстик: x={x:.2f}, y={y:.2f}')
            self.cmd_vel_pub.publish(twist)
        
        # Запуск сервера
        socketio.run(app, host='0.0.0.0', port=self.port, debug=False, allow_unsafe_werkzeug=True)
    
    def destroy_node(self):
        self.get_logger().info('🛑 Остановка веб-панели')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = UnifiedWebNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()