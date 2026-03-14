# web_controller.py - Добавим к существующей системе
from flask import Flask, render_template, jsonify, request
import threading
import json

app = Flask(__name__)

# Подключаемся к нашему роботу
from robot_movement import RobotControl
robot = RobotControl()

@app.route('/')
def index():
    return render_template('controller.html')

@app.route('/api/command', methods=['POST'])
def command():
    cmd = request.json.get('command')
    robot.execute_command(cmd)
    return jsonify({'status': 'ok', 'command': cmd})

@app.route('/api/status')
def status():
    motor_status = robot.motors.get_status()
    return jsonify(motor_status)

def start_web_server():
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

# Запускаем веб-сервер в отдельном потоке
web_thread = threading.Thread(target=start_web_server)
web_thread.daemon = True
web_thread.start()

# Запускаем обычное управление с клавиатуры
robot.run()