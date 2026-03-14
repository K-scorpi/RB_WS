#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
import subprocess
import threading
import numpy as np
import cv2
import os
import signal
import time
from cv_bridge import CvBridge

class RPiCamNode(Node):
    """ROS2 нода для камеры через rpicam-vid"""
    
    def __init__(self):
        super().__init__('rpicam_node')
        
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('framerate', 30)
        self.declare_parameter('rotation', 180)
        self.declare_parameter('camera_frame_id', 'camera_link')
        
        self.width = self.get_parameter('width').value
        self.height = self.get_parameter('height').value
        self.framerate = self.get_parameter('framerate').value
        self.rotation = self.get_parameter('rotation').value
        self.frame_id = self.get_parameter('camera_frame_id').value
        
        self.bridge = CvBridge()
        self.image_pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self.status_pub = self.create_publisher(String, 'camera/status', 10)
        
        self.get_logger().info('🚀 ЗАПУСК КАМЕРЫ ЧЕРЕЗ RPICAM')
        self.get_logger().info(f'📐 Разрешение: {self.width}x{self.height}')
        self.get_logger().info(f'⏱️ FPS: {self.framerate}')
        self.get_logger().info(f'🔄 Поворот: {self.rotation}°')
        
        self.process = None
        self.running = True
        self.camera_available = False
        
        # Создаем именованный канал
        self.pipe_path = '/tmp/rpicam_pipe'
        if os.path.exists(self.pipe_path):
            os.unlink(self.pipe_path)
        os.mkfifo(self.pipe_path)
        
        # Запускаем rpicam
        self.start_rpicam()
        
        # Поток для чтения данных
        self.read_thread = threading.Thread(target=self.read_pipe)
        self.read_thread.daemon = True
        self.read_thread.start()
        
        self.create_timer(1.0, self.publish_status)
        
    def start_rpicam(self):
        cmd = [
            'rpicam-vid',
            '--width', str(self.width),
            '--height', str(self.height),
            '--framerate', str(self.framerate),
            '--codec', 'yuv420',
            '--output', self.pipe_path,
            '--timeout', '0',
            '--nopreview',
            '--rotation', str(self.rotation)
        ]
        
        self.get_logger().info(f'📹 Запуск: {" ".join(cmd)}')
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.camera_available = True
            self.get_logger().info('✅ rpicam-vid запущен')
        except Exception as e:
            self.get_logger().error(f'❌ Ошибка запуска rpicam: {e}')
            
    def read_pipe(self):
        frame_size = self.width * self.height * 3 // 2
        
        self.get_logger().info('📥 Ожидание данных...')
        
        with open(self.pipe_path, 'rb') as fifo:
            while self.running and self.process and self.process.poll() is None:
                try:
                    data = fifo.read(frame_size)
                    
                    if len(data) == frame_size:
                        yuv = np.frombuffer(data, dtype=np.uint8).reshape(
                            (self.height * 3 // 2, self.width)
                        )
                        bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
                        
                        ros_image = self.bridge.cv2_to_imgmsg(bgr, 'bgr8')
                        ros_image.header.stamp = self.get_clock().now().to_msg()
                        ros_image.header.frame_id = self.frame_id
                        self.image_pub.publish(ros_image)
                        
                    else:
                        self.get_logger().warn(f'⚠️ Неполный кадр: {len(data)}/{frame_size}')
                        
                except Exception as e:
                    self.get_logger().error(f'❌ Ошибка чтения: {e}')
                    break
                    
        self.get_logger().info('📴 Поток чтения завершен')
        
    def publish_status(self):
        msg = String()
        if self.camera_available and self.process and self.process.poll() is None:
            msg.data = f"ACTIVE {self.width}x{self.height} rpicam"
        else:
            msg.data = "ERROR - rpicam not running"
        self.status_pub.publish(msg)
        
    def destroy_node(self):
        self.get_logger().info('🛑 Остановка камеры...')
        self.running = False
        
        if self.process:
            self.process.terminate()
            self.process.wait()
            
        if os.path.exists(self.pipe_path):
            os.unlink(self.pipe_path)
            
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RPiCamNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
