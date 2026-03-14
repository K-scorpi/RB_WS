#!/usr/bin/env python3
# robot_movement.py
# Управление моторами через L298N с дисплеем

import RPi.GPIO as GPIO
import time
import threading
from display_controller import DisplayController

class MotorController:
    """Класс для управления моторами через L298N"""
    
    def __init__(self):
        # Пины для моторов (как у тебя)
        self.IN1 = 17  # левый мотор направление 1
        self.IN2 = 16  # левый мотор направление 2
        self.IN3 = 15  # правый мотор направление 1
        self.IN4 = 14  # правый мотор направление 2
        
        # Настройка GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([self.IN1, self.IN2, self.IN3, self.IN4], GPIO.OUT)
        
        # Состояние моторов
        self.left_dir = 0   # -1 назад, 0 стоп, 1 вперед
        self.right_dir = 0  # -1 назад, 0 стоп, 1 вперед
        self.speed = 100     # скорость в % (пока 100%)
        
        # Останавливаем моторы при старте
        self.stop()
        
        print("\n" + "="*50)
        print("МОТОРЫ ИНИЦИАЛИЗИРОВАНЫ")
        print("="*50)
        print(f"Левый мотор: IN1={self.IN1}, IN2={self.IN2}")
        print(f"Правый мотор: IN3={self.IN3}, IN4={self.IN4}")
        print(f"Режим: {self.speed}% скорость (перемычки ENA/ENB)")
        print("="*50 + "\n")
    
    def set_left_motor(self, direction):
        """
        Управление левым мотором
        direction: 1 - вперед, -1 - назад, 0 - стоп
        """
        if direction == 1:  # Вперед
            GPIO.output(self.IN1, GPIO.HIGH)
            GPIO.output(self.IN2, GPIO.LOW)
            self.left_dir = 1
        elif direction == -1:  # Назад
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.HIGH)
            self.left_dir = -1
        else:  # Стоп
            GPIO.output(self.IN1, GPIO.LOW)
            GPIO.output(self.IN2, GPIO.LOW)
            self.left_dir = 0
    
    def set_right_motor(self, direction):
        """
        Управление правым мотором
        direction: 1 - вперед, -1 - назад, 0 - стоп
        """
        if direction == 1:  # Вперед
            GPIO.output(self.IN3, GPIO.HIGH)
            GPIO.output(self.IN4, GPIO.LOW)
            self.right_dir = 1
        elif direction == -1:  # Назад
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.HIGH)
            self.right_dir = -1
        else:  # Стоп
            GPIO.output(self.IN3, GPIO.LOW)
            GPIO.output(self.IN4, GPIO.LOW)
            self.right_dir = 0
    
    def forward(self):
        """Оба мотора вперед"""
        self.set_left_motor(1)
        self.set_right_motor(1)
        print("  ✓ Едем ВПЕРЕД")
    
    def backward(self):
        """Оба мотора назад"""
        self.set_left_motor(-1)
        self.set_right_motor(-1)
        print("  ✓ Едем НАЗАД")
    
    def turn_left(self):
        """Поворот налево (левая назад, правая вперед)"""
        self.set_left_motor(-1)
        self.set_right_motor(1)
        print("  ✓ Поворот НАЛЕВО")
    
    def turn_right(self):
        """Поворот направо (левая вперед, правая назад)"""
        self.set_left_motor(1)
        self.set_right_motor(-1)
        print("  ✓ Поворот НАПРАВО")
    
    def stop(self):
        """Остановка всех моторов"""
        self.set_left_motor(0)
        self.set_right_motor(0)
        print("  ✓ СТОП")
    
    def get_status(self):
        """Получить статус моторов"""
        return {
            'left': self.left_dir,
            'right': self.right_dir,
            'speed': self.speed
        }
    
    def test_sequence(self):
        """Тестовая последовательность для проверки моторов"""
        print("\n🔧 ТЕСТОВАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ")
        print("Проверьте направление каждого мотора:\n")
        
        input("Нажмите Enter для теста ЛЕВЫЙ ВПЕРЕД...")
        self.set_left_motor(1)
        self.set_right_motor(0)
        time.sleep(2)
        self.stop()
        
        input("Нажмите Enter для теста ЛЕВЫЙ НАЗАД...")
        self.set_left_motor(-1)
        self.set_right_motor(0)
        time.sleep(2)
        self.stop()
        
        input("Нажмите Enter для теста ПРАВЫЙ ВПЕРЕД...")
        self.set_left_motor(0)
        self.set_right_motor(1)
        time.sleep(2)
        self.stop()
        
        input("Нажмите Enter для теста ПРАВЫЙ НАЗАД...")
        self.set_left_motor(0)
        self.set_right_motor(-1)
        time.sleep(2)
        self.stop()
        
        input("Нажмите Enter для теста ОБА ВПЕРЕД...")
        self.forward()
        time.sleep(2)
        self.stop()
        
        input("Нажмите Enter для теста ПОВОРОТ НАЛЕВО...")
        self.turn_left()
        time.sleep(2)
        self.stop()
        
        input("Нажмите Enter для теста ПОВОРОТ НАПРАВО...")
        self.turn_right()
        time.sleep(2)
        self.stop()
        
        print("\n✅ Тест завершен")
    
    def cleanup(self):
        """Очистка GPIO"""
        self.stop()
        GPIO.cleanup()


class RobotControl:
    """Основной класс управления роботом"""
    
    def __init__(self):
        # Инициализация дисплея
        try:
            self.display = DisplayController(rotation=90)
            self.display_available = True
        except Exception as e:
            print(f"❌ Ошибка инициализации дисплея: {e}")
            self.display = None
            self.display_available = False
        
        # Инициализация моторов
        self.motors = MotorController()
        
        # Флаг работы
        self.running = True
        
        # Показываем заставку
        if self.display_available:
            self.display.show_splash()
            time.sleep(2)
    
    def update_display(self):
        """Обновить дисплей"""
        if self.display_available:
            status = self.motors.get_status()
            self.display.show_robot_status(
                status['left'], 
                status['right'], 
                status['speed']
            )
    
    def execute_command(self, cmd):
        """Выполнить команду"""
        cmd = cmd.lower().strip()
        
        if cmd == 'w':
            self.motors.forward()
        elif cmd == 's':
            self.motors.backward()
        elif cmd == 'a':
            self.motors.turn_left()
        elif cmd == 'd':
            self.motors.turn_right()
        elif cmd == 'x':
            self.motors.stop()
        elif cmd == 'q':
            self.running = False
            print("  ✓ Выход из программы")
        elif cmd == 't':
            self.motors.test_sequence()
        elif cmd == 'h':
            self.show_help()
        else:
            print(f"  ⚠ Неизвестная команда: {cmd}")
        
        # Обновляем дисплей после каждой команды
        self.update_display()
    
    def show_help(self):
        """Показать справку"""
        print("\n" + "="*50)
        print("ДОСТУПНЫЕ КОМАНДЫ")
        print("="*50)
        print("  W - Вперед")
        print("  S - Назад")
        print("  A - Поворот налево")
        print("  D - Поворот направо")
        print("  X - Стоп")
        print("  T - Тест моторов")
        print("  H - Эта справка")
        print("  Q - Выход")
        print("="*50 + "\n")
    
    def run(self):
        """Запуск управления"""
        print("\n" + "="*50)
        print("РОБОТ НА ГУСЕНИЦАХ")
        print("="*50)
        
        self.show_help()
        
        # Обновляем дисплей
        self.update_display()
        
        try:
            while self.running:
                cmd = input("Команда > ")
                self.execute_command(cmd)
                
        except KeyboardInterrupt:
            print("\n\n⚠ Программа прервана пользователем")
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Очистка ресурсов"""
        print("\nОчистка ресурсов...")
        self.motors.cleanup()
        if self.display_available:
            self.display.close()
        print("✅ Программа завершена")


if __name__ == "__main__":
    robot = RobotControl()
    robot.run()