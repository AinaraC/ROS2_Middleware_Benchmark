import rclpy
from rclpy.node import Node
from std_msgs.msg import Header
import time

class LatencyPublisher(Node):
    def __init__(self):
        super().__init__('latency_publisher')
        self.publisher_ = self.create_publisher(Header, 'latency_topic', 10)
        timer_period = 0.05  # 20 Hz
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.count = 0
        self.get_logger().info('Latency publisher started')

    def timer_callback(self):
        msg = Header()
        msg.stamp = self.get_clock().now().to_msg()  # Marca temporal del envío
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
