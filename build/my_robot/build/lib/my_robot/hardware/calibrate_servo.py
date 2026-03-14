#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

def calibrate(pin, name):
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)
    
    pwm = GPIO.PWM(pin, 50)  # 50 Гц
    pwm.start(0)
    
    print(f"\nКалибровка {name} (пин {pin})")
    print("Вводи значения duty cycle от 2.5 до 12.5")
    print("Найди:")
    print("  - Минимальное значение, при котором серво начинает двигаться")
    print("  - Максимальное значение перед упором")
    print("  - Центральное положение (обычно 7.5)")
    print("'q' для выхода\n")
    
    try:
        while True:
            val = input("duty cycle (%): ")
            if val == 'q':
                break
            try:
                duty = float(val)
                pwm.ChangeDutyCycle(duty)
                print(f"  Установлено {duty}%")
                time.sleep(0.5)
            except:
                print("Неверное значение")
    finally:
        pwm.stop()
        GPIO.cleanup()

if __name__ == "__main__":
    print("Калибровка сервоприводов")
    print("Подключи питание к серво!")
    
    # Калибруем pan (пин 5)
    calibrate(5, "Pan (поворот)")
    
    # Калибруем tilt (пин 6)
    calibrate(6, "Tilt (наклон)")