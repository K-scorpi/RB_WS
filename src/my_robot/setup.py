from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'my_robot'

setup(
    name=package_name,
    version='0.0.2',
    packages=find_packages(exclude=['test']),  # Изменено здесь
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'params'), glob('params/*.yaml')),
        (os.path.join('share', package_name, 'web/templates'), glob('my_robot/web/templates/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='admin',
    maintainer_email='admin@local',
    description='ROS2 package for tracked robot',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'motor_node = my_robot.hardware.motor_node:main',
            'display_node = my_robot.display.display_node:main',
            'unified_web_node = my_robot.web.unified_web_node:main',
            'servo_node = my_robot.hardware.servo_node:main',
        ],
    },
)