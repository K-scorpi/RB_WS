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
import time
import socket
import select
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
from cv_bridge import CvBridge

class RPiCamWebNode(Node):
    """Камера через rpicam-vid с веб-стримом"""
    
    def __init__(self):
        super().__init__('rpicam_web_node')
        
        # Параметры
        self.declare_parameter('width', 640)
        self.declare_parameter('height', 480)
        self.declare_parameter('fps', 30)
        self.declare_parameter('port', 8080)
        self.declare_parameter('rotate', 180)
        
        self.width = self.get_parameter('width').value
        self.height = self.get_parameter('height').value
        self.fps = self.get_parameter('fps').value
        self.port = self.get_parameter('port').value
        self.rotate = self.get_parameter('rotate').value
        
        self.get_logger().info('=' * 50)
        self.get_logger().info('📷 RPICAM WEB CAMERA')
        self.get_logger().info('=' * 50)
        self.get_logger().info(f'Разрешение: {self.width}x{self.height}')
        self.get_logger().info(f'FPS: {self.fps}')
        self.get_logger().info(f'Порт: {self.port}')
        self.get_logger().info(f'Поворот: {self.rotate}°')
        
        self.bridge = CvBridge()
        self.image_pub = self.create_publisher(Image, 'camera/image_raw', 10)
        self.status_pub = self.create_publisher(String, 'camera/status', 10)
        
        self.running = True
        self.last_jpeg = None
        self.frame_lock = threading.Lock()
        self.frame_count = 0
        self.fps_counter = 0
        
        # Запускаем rpicam
        self.camera_thread = threading.Thread(target=self.rpicam_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        # Запускаем веб-сервер
        self.start_web_server()
        
        self.create_timer(1.0, self.publish_status)
        self.create_timer(1.0, self.log_fps)
    
    def log_fps(self):
        self.get_logger().info(f'📊 FPS: {self.fps_counter}')
        self.fps_counter = 0
    
    def rpicam_loop(self):
        pipe_path = '/tmp/rpicam_pipe'
        if os.path.exists(pipe_path):
            os.unlink(pipe_path)
        
        try:
            os.mkfifo(pipe_path)
            self.get_logger().info(f'📁 Создан pipe: {pipe_path}')
        except Exception as e:
            self.get_logger().error(f'❌ Ошибка создания pipe: {e}')
            return
        
        cmd = [
            'rpicam-vid',
            '--width', str(self.width),
            '--height', str(self.height),
            '--framerate', str(self.fps),
            '--codec', 'yuv420',
            '--output', pipe_path,
            '--timeout', '0',
            '--nopreview',
            '--rotation', str(self.rotate)
        ]
        
        self.get_logger().info(f'🚀 Запуск: {" ".join(cmd)}')
        
        process = None
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)
            
            if process.poll() is not None:
                stderr = process.stderr.read().decode()
                self.get_logger().error(f'❌ Процесс завершился: {stderr}')
                return
            
            self.get_logger().info('✅ rpicam-vid запущен')
            
            with open(pipe_path, 'rb') as fifo:
                frame_size = self.width * self.height * 3 // 2
                self.get_logger().info(f'📥 Ожидание данных (размер кадра: {frame_size} bytes)')
                
                while self.running:
                    ready, _, _ = select.select([fifo], [], [], 1.0)
                    if not ready:
                        continue
                    
                    data = fifo.read(frame_size)
                    
                    if len(data) == frame_size:
                        self.frame_count += 1
                        self.fps_counter += 1
                        
                        try:
                            yuv = np.frombuffer(data, dtype=np.uint8).reshape(
                                (self.height * 3 // 2, self.width)
                            )
                            bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
                            
                            # Конвертируем в JPEG
                            _, jpeg = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            jpeg_bytes = jpeg.tobytes()
                            
                            # Обновляем кадр для веба
                            with self.frame_lock:
                                self.last_jpeg = jpeg_bytes
                            
                            # Публикуем в ROS (каждый 3-й кадр)
                            if self.frame_count % 3 == 0:
                                ros_image = self.bridge.cv2_to_imgmsg(bgr, 'bgr8')
                                ros_image.header.stamp = self.get_clock().now().to_msg()
                                ros_image.header.frame_id = 'camera_link'
                                self.image_pub.publish(ros_image)
                            
                            if self.frame_count % 30 == 0:
                                self.get_logger().info(f'📸 Получено кадров: {self.frame_count}')
                                
                        except Exception as e:
                            self.get_logger().error(f'❌ Ошибка конвертации: {e}')
                    else:
                        self.get_logger().warn(f'⚠️ Неполный кадр: {len(data)}/{frame_size}')
                        
        except Exception as e:
            self.get_logger().error(f'❌ Ошибка: {e}')
        finally:
            if process:
                process.terminate()
                process.wait()
            if os.path.exists(pipe_path):
                os.unlink(pipe_path)
            self.get_logger().info('📴 Поток камеры завершен')
    
    def start_web_server(self):
        class VideoHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    
                    html = f'''
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Robot Camera</title>
                        <style>
                            body {{ background: #1a1a1a; color: white; font-family: Arial; text-align: center; }}
                            .container {{ max-width: 800px; margin: 0 auto; padding: 20px; }}
                            .video-container {{ background: #000; border-radius: 10px; overflow: hidden; }}
                            img {{ width: 100%; height: auto; }}
                            .status {{ margin: 10px 0; color: #4CAF50; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <h1>🤖 ROBOT CAMERA</h1>
                            <div class="video-container">
                                <img src="/video_feed" id="videoFeed">
                            </div>
                            <div class="status">
                                Разрешение: {self.server.width}x{self.server.height} | FPS: {self.server.fps}
                            </div>
                        </div>
                        <script>
                            const img = document.getElementById('videoFeed');
                            setInterval(() => {{
                                img.src = '/video_feed?t=' + Date.now();
                            }}, 50);
                        </script>
                    </body>
                    </html>
                    '''
                    self.wfile.write(html.encode())
                    
                elif self.path.startswith('/video_feed'):
                    self.send_response(200)
                    self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Pragma', 'no-cache')
                    self.send_header('Expires', '0')
                    self.end_headers()
                    
                    while True:
                        if self.server.last_jpeg:
                            try:
                                self.wfile.write(b'--frame\r\n')
                                self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                                self.wfile.write(self.server.last_jpeg)
                                self.wfile.write(b'\r\n')
                            except:
                                break
                        time.sleep(0.03)
                else:
                    self.send_response(404)
                    self.end_headers()
        
        class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
            allow_reuse_address = True
        
        # Создаем сервер и сохраняем в него данные
        self.server = ThreadedHTTPServer(('0.0.0.0', self.port), VideoHandler)
        self.server.last_jpeg = None
        self.server.width = self.width
        self.server.height = self.height
        self.server.fps = self.fps
        self.server.frame_lock = self.frame_lock
        
        # Функция обновления last_jpeg в сервере
        def update_server_jpeg():
            while self.running:
                with self.frame_lock:
                    self.server.last_jpeg = self.last_jpeg
                time.sleep(0.01)
        
        self.updater_thread = threading.Thread(target=update_server_jpeg)
        self.updater_thread.daemon = True
        self.updater_thread.start()
        
        # Запускаем сервер
        def run_server():
            self.get_logger().info(f'🌐 Веб-сервер на http://0.0.0.0:{self.port}')
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(('8.8.8.8', 80))
                ip = s.getsockname()[0]
                s.close()
                self.get_logger().info(f'📱 Доступно по IP: http://{ip}:{self.port}')
            except:
                pass
            self.server.serve_forever()
        
        self.web_thread = threading.Thread(target=run_server)
        self.web_thread.daemon = True
        self.web_thread.start()
    
    def publish_status(self):
        msg = String()
        if self.last_jpeg is not None:
            msg.data = f"ACTIVE {self.width}x{self.height}"
        else:
            msg.data = "STARTING"
        self.status_pub.publish(msg)
    
    def destroy_node(self):
        self.get_logger().info('🛑 Остановка...')
        self.running = False
        if hasattr(self, 'server'):
            self.server.shutdown()
        if hasattr(self, 'camera_thread'):
            self.camera_thread.join(timeout=2.0)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = RPiCamWebNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()