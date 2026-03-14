from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
import os  # ← ЭТО ВАЖНО!
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='my_robot',
            executable='motor_node',
            name='motor_controller',
            output='screen',
        ),
        Node(
            package='my_robot',
            executable='display_node',
            name='display',
            output='screen',
        ),
        Node(
            package='my_robot',
            executable='servo_node',
            name='servo_controller',
            output='screen',
            parameters=[{
                'pan_pin': 5,
                'tilt_pin': 6,
                'pan_min_duty': 2.5,
                'pan_max_duty': 12.0,
                'tilt_min_duty': 2.5,
                'tilt_max_duty': 8.0,
            }]
        ),
        
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory('robot_camera'),
                    'launch/camera.launch.py'
                )
            ),
            launch_arguments={
                'width': '640',
                'height': '480',
                'flip': 'rotate=180',
            }.items()
        ),
    ])