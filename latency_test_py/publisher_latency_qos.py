import rclpy
from rclpy.node import Node
from std_msgs.msg import Header
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import time

class LatencyPublisher(Node):
    def __init__(self):
        super().__init__('latency_publisher')

        # Parámetros: frecuencia y modo de fiabilidad
        self.declare_parameter('publish_rate', 20.0)  # Hz
        self.declare_parameter('reliability', 'reliable')  # reliable | best_effort

        rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        reliability_str = self.get_parameter('reliability').get_parameter_value().string_value

        # Configura el perfil QoS
        reliability = ReliabilityPolicy.RELIABLE if reliability_str == 'reliable' else ReliabilityPolicy.BEST_EFFORT
        qos_profile = QoSProfile(
            reliability=reliability,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Crea el publicador con QoS seleccionado
        self.publisher_ = self.create_publisher(Header, 'latency_topic', qos_profile)
        self.timer = self.create_timer(1.0 / rate, self.timer_callback)
        self.count = 0

        self.get_logger().info(f'Publisher started ({reliability_str.upper()}, {rate:.1f} Hz)')

    def timer_callback(self):
        msg = Header()
        msg.stamp = self.get_clock().now().to_msg()
        msg.frame_id = str(self.count)
        self.publisher_.publish(msg)
        self.count += 1

def main(args=None):
    rclpy.init(args=args)
    node = LatencyPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
