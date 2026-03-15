from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('width', default_value='640'),
        DeclareLaunchArgument('height', default_value='480'),
        DeclareLaunchArgument('fps', default_value='30'),
        DeclareLaunchArgument('port', default_value='8080'),
        DeclareLaunchArgument('rotate', default_value='true'),
        
        Node(
            package='robot_camera',
            executable='web_camera_node',
            name='web_camera_node',
            output='screen',
            parameters=[{
                'width': LaunchConfiguration('width'),
                'height': LaunchConfiguration('height'),
                'fps': LaunchConfiguration('fps'),
                'port': LaunchConfiguration('port'),
                'rotate': LaunchConfiguration('rotate'),
            }]
        ),
    ])
