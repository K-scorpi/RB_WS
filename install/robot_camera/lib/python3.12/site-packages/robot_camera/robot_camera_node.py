#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String
import cv2
from cv_bridge import CvBridge
import threading
import time

class RobotCameraNode(Node):
    def __init__(self):
        super().__init__('robot_camera_node')
        
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('framerate', 30)
        self.declare_parameter('flip', 'rotate=180')
        
        self.width = self.get_parameter('width').value
        self.height = self.get_parameter('height').value
        self.framerate = self.get_parameter('framerate').value
        self.flip = self.get_parameter('flip').value
        
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, 'camera/image_raw', 10)
        self.status_pub = self.create_publisher(String, 'camera/status', 10)
        
        self.get_logger().info(f'Инициализация камеры {self.width}x{self.height}')
        
        self.running = True
        self.cap = None
        self.camera_thread = threading.Thread(target=self.camera_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        self.create_timer(1.0, self.publish_status)
    
    def camera_loop(self):
        self.get_logger().info('Открываю камеру...')
        self.cap = cv2.VideoCapture(0)
        
        if not self.cap.isOpened():
            self.get_logger().error('Не удалось открыть камеру!')
            return
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.framerate)
        
        self.get_logger().info('✅ Камера открыта')
        
        while self.running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                if self.flip == 'rotate=180':
                    frame = cv2.rotate(frame, cv2.ROTATE_180)
                
                msg = self.bridge.cv2_to_imgmsg(frame, 'bgr8')
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.header.frame_id = 'camera_link'
                self.publisher.publish(msg)
            else:
                self.get_logger().warn('Ошибка чтения кадра')
                time.sleep(0.1)
        
        if self.cap:
            self.cap.release()
        self.get_logger().info('Камера остановлена')
    
    def publish_status(self):
        msg = String()
        msg.data = f"ACTIVE {self.width}x{self.height}"
        self.status_pub.publish(msg)
    
    def destroy_node(self):
        self.running = False
        if self.camera_thread.is_alive():
            self.camera_thread.join(timeout=2.0)
        super().destroy_node()

def main(args=None):
    rclpy.init(args=args)
    node = RobotCameraNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
