from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_camera'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='admin',
    maintainer_email='admin@localhost.com',
    description='ROS2 camera node for Raspberry Pi using rpicam',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'rpicam_node = robot_camera.rpicam_node:main',
        ],
    },
)