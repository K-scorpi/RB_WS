from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('width', default_value='640'),
        DeclareLaunchArgument('height', default_value='480'),
        DeclareLaunchArgument('framerate', default_value='30'),
        DeclareLaunchArgument('rotation', default_value='180'),
        
        Node(
            package='robot_camera',
            executable='rpicam_node',
            name='rpicam_node',
            output='screen',
            parameters=[{
                'width': LaunchConfiguration('width'),
                'height': LaunchConfiguration('height'),
                'framerate': LaunchConfiguration('framerate'),
                'rotation': LaunchConfiguration('rotation'),
            }]
        ),
    ])