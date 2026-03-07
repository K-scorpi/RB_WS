from launch import LaunchDescription
from launch_ros.actions import Node

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
    ])