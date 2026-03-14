#!/usr/bin/env python3
# display_controller.py
# Класс для управления WaveShare ST7789 дисплеем

import spidev
import RPi.GPIO as GPIO
import time
from PIL import Image, ImageDraw, ImageFont

class DisplayController:
    """Класс для управления WaveShare ST7789 дисплеем"""
    
    def __init__(self, rotation=90):
        # Пины из твоего кода
        self.CS = 8    # GPIO8 (CE0)
        self.DC = 25   # GPIO25
        self.RST = 24  # GPIO24
        self.rotation = rotation
        
        # Настройка GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.CS, GPIO.OUT)
        GPIO.setup(self.DC, GPIO.OUT)
        GPIO.setup(self.RST, GPIO.OUT)
        GPIO.output(self.CS, GPIO.HIGH)
        
        # Настройка SPI
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 20000000  # 20 MHz
        self.spi.mode = 0
        
        # Разрешение дисплея
        if rotation == 0 or rotation == 180:
            self.width = 170
            self.height = 320
        else:  # 90 или 270 градусов
            self.width = 320
            self.height = 170
        
        # Инициализация
        self.reset()
        self.init_display()
        
        # Создаем изображение для работы
        self.image = Image.new("RGB", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        
        # Загрузка шрифтов
        self.load_fonts()
        
        print(f"✅ Дисплей инициализирован (поворот {rotation}°)")
        print(f"📐 Разрешение: {self.width} x {self.height}")
    
    def load_fonts(self):
        """Загрузка шрифтов"""
        try:
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
            self.font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            print("⚠️ Используются шрифты по умолчанию")
    
    def reset(self):
        """Сброс дисплея"""
        GPIO.output(self.RST, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(self.RST, GPIO.HIGH)
        time.sleep(0.1)
    
    def write_cmd(self, cmd):
        """Отправка команды"""
        GPIO.output(self.DC, GPIO.LOW)
        GPIO.output(self.CS, GPIO.LOW)
        self.spi.xfer2([cmd])
        GPIO.output(self.CS, GPIO.HIGH)
    
    def write_data(self, data):
        """Отправка данных"""
        GPIO.output(self.DC, GPIO.HIGH)
        GPIO.output(self.CS, GPIO.LOW)
        if isinstance(data, list):
            self.spi.xfer2(data)
        else:
            self.spi.xfer2([data])
        GPIO.output(self.CS, GPIO.HIGH)
    
    def init_display(self):
        """Инициализация для WaveShare 1.9" ST7789"""
        # Software reset
        self.write_cmd(0x01)
        time.sleep(0.15)
        
        # Sleep out
        self.write_cmd(0x11)
        time.sleep(0.15)
        
        # Memory access control (ориентация)
        self.write_cmd(0x36)
        if self.rotation == 0:
            self.write_data(0x00)  # 0 градусов
        elif self.rotation == 90:
            self.write_data(0x60)  # 90 градусов (MV=1, MX=0, MY=0)
        elif self.rotation == 180:
            self.write_data(0xC0)  # 180 градусов
        elif self.rotation == 270:
            self.write_data(0xA0)  # 270 градусов
        
        # Pixel format (16-bit)
        self.write_cmd(0x3A)
        self.write_data(0x05)
        
        # Display on
        self.write_cmd(0x29)
        time.sleep(0.15)
    
    def set_window(self, x0, y0, x1, y1):
        """Установка области для записи"""
        self.write_cmd(0x2A)  # Column
        self.write_data([(x0 >> 8) & 0xFF, x0 & 0xFF, (x1 >> 8) & 0xFF, x1 & 0xFF])
        
        self.write_cmd(0x2B)  # Row
        self.write_data([(y0 >> 8) & 0xFF, y0 & 0xFF, (y1 >> 8) & 0xFF, y1 & 0xFF])
        
        self.write_cmd(0x2C)  # Memory write
    
    def display_image(self, image=None):
        """Отображение PIL изображения"""
        if image is None:
            image = self.image
        
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Изменяем размер если нужно
        if image.size != (self.width, self.height):
            image = image.resize((self.width, self.height))
        
        self.set_window(0, 0, self.width-1, self.height-1)
        
        GPIO.output(self.DC, GPIO.HIGH)
        GPIO.output(self.CS, GPIO.LOW)
        
        # Конвертация RGB888 в RGB565 и отправка
        pixels = list(image.getdata())
        for r, g, b in pixels:
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            self.spi.xfer2([(rgb565 >> 8) & 0xFF, rgb565 & 0xFF])
        
        GPIO.output(self.CS, GPIO.HIGH)
    
    def clear(self, color=(0, 0, 0)):
        """Очистка экрана цветом"""
        self.draw.rectangle((0, 0, self.width, self.height), fill=color)
        self.display_image()
    
    def show_text(self, text, x=10, y=10, color=(255, 255, 255), font_size='medium'):
        """Показать текст на дисплее"""
        if font_size == 'large':
            font = self.font_large
        elif font_size == 'medium':
            font = self.font_medium
        else:
            font = self.font_small
        
        self.draw.text((x, y), text, fill=color, font=font)
    
    def show_robot_status(self, left_dir, right_dir, speed=100):
        """
        Показать статус робота на дисплее
        left_dir: 1 - вперед, -1 - назад, 0 - стоп
        right_dir: 1 - вперед, -1 - назад, 0 - стоп
        """
        # Очистка
        self.draw.rectangle((0, 0, self.width, self.height), fill=(0, 0, 0))
        
        # Рамка
        self.draw.rectangle((2, 2, self.width-2, self.height-2), outline=(0, 100, 0))
        
        # Заголовок
        self.draw.text((10, 5), "ROBOT CONTROL", fill=(0, 255, 0), font=self.font_medium)
        
        # Разделитель
        self.draw.line([(5, 35), (self.width-5, 35)], fill=(100, 100, 100))
        
        # Функция для преобразования направления в стрелку
        def dir_to_arrow(d):
            if d == 1:
                return "▲"
            elif d == -1:
                return "▼"
            else:
                return "■"
        
        # Функция для преобразования направления в текст
        def dir_to_text(d):
            if d == 1:
                return "FWD"
            elif d == -1:
                return "REV"
            else:
                return "STOP"
        
        # Левая гусеница
        y = 45
        self.draw.text((10, y), "LEFT:", fill=(0, 255, 0), font=self.font_small)
        self.draw.text((80, y), dir_to_arrow(left_dir), fill=(255, 255, 255), font=self.font_large)
        self.draw.text((120, y+5), dir_to_text(left_dir), fill=(200, 200, 200), font=self.font_small)
        
        # Правая гусеница
        y = 85
        self.draw.text((10, y), "RIGHT:", fill=(0, 255, 0), font=self.font_small)
        self.draw.text((80, y), dir_to_arrow(right_dir), fill=(255, 255, 255), font=self.font_large)
        self.draw.text((120, y+5), dir_to_text(right_dir), fill=(200, 200, 200), font=self.font_small)
        
        # Скорость
        self.draw.text((10, 125), f"SPEED: {speed}%", fill=(255, 255, 0), font=self.font_small)
        
        # Время
        current_time = time.strftime("%H:%M:%S")
        self.draw.text((self.width-100, self.height-25), current_time, fill=(100, 100, 255), font=self.font_small)
        
        # Отображаем
        self.display_image()
    
    def show_splash(self):
        """Показать заставку"""
        self.draw.rectangle((0, 0, self.width, self.height), fill=(0, 0, 50))
        self.draw.text((10, 50), "ROBOT", fill=(0, 255, 0), font=self.font_large)
        self.draw.text((10, 80), "CONTROLLER", fill=(0, 255, 0), font=self.font_large)
        self.draw.text((10, 120), "v1.0", fill=(255, 255, 255), font=self.font_medium)
        self.draw.text((10, 150), "WASD - control", fill=(200, 200, 200), font=self.font_small)
        self.draw.text((10, 170), "X - stop", fill=(200, 200, 200), font=self.font_small)
        self.draw.text((10, 190), "Q - quit", fill=(200, 200, 200), font=self.font_small)
        self.display_image()
    
    def show_temperature(self, temp_c, cpu_temp=None):
        """Показать температуру (как в твоем примере)"""
        self.draw.rectangle((0, 0, self.width, self.height), fill=(0, 0, 0))
        
        # Рамка
        self.draw.rectangle((2, 2, self.width-2, self.height-2), outline=(0, 100, 0))
        
        # Заголовок
        self.draw.text((10, 10), "Temperature", fill=(0, 255, 0), font=self.font_medium)
        
        if temp_c is not None:
            # Большая температура в C
            temp_text = f"{temp_c:.1f}°C"
            self.draw.text((10, 40), temp_text, fill=(255, 255, 0), font=self.font_large)
            
            # Температура в F
            temp_f = temp_c * 9.0/5.0 + 32.0
            self.draw.text((10, 70), f"{temp_f:.1f}°F", fill=(180, 180, 180), font=self.font_medium)
            
            # Цветная полоса
            bar_width = int((temp_c + 20) * 3)
            if bar_width < 0:
                bar_width = 0
            if bar_width > self.width - 20:
                bar_width = self.width - 20
            
            if temp_c < 10:
                bar_color = (0, 0, 255)
            elif temp_c < 25:
                bar_color = (0, 255, 0)
            else:
                bar_color = (255, 0, 0)
            
            self.draw.rectangle((10, 100, 10 + bar_width, 115), fill=bar_color)
            self.draw.rectangle((10, 100, self.width-10, 115), outline=(100, 100, 100))
        else:
            self.draw.text((10, 40), "Ошибка чтения", fill=(255, 0, 0), font=self.font_medium)
            self.draw.text((10, 70), "датчика", fill=(255, 0, 0), font=self.font_medium)
        
        # Время и дата
        current_time = time.strftime("%H:%M:%S")
        current_date = time.strftime("%d.%m.%Y")
        
        self.draw.text((10, 130), current_date, fill=(100, 100, 255), font=self.font_small)
        self.draw.text((10, 150), current_time, fill=(100, 255, 100), font=self.font_medium)
        
        # CPU температура
        if cpu_temp:
            self.draw.text((10, 175), f"CPU: {cpu_temp:.1f}°C", fill=(255, 100, 100), font=self.font_small)
        
        self.display_image()
    
    def close(self):
        """Очистка ресурсов"""
        self.clear()
        GPIO.cleanup()
        self.spi.close()


# Пример использования если файл запущен отдельно
if __name__ == "__main__":
    print("Тест дисплея")
    display = DisplayController(rotation=90)
    
    # Тест заставки
    display.show_splash()
    time.sleep(2)
    
    # Тест статуса робота
    display.show_robot_status(1, 1)  # обе вперед
    time.sleep(2)
    
    display.show_robot_status(-1, 1)  # поворот налево
    time.sleep(2)
    
    # Тест температуры
    display.show_temperature(23.5, 45.2)
    time.sleep(2)
    
    display.close()
    print("Тест завершен")