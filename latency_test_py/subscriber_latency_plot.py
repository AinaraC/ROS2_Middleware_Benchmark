import rclpy
from rclpy.node import Node
from std_msgs.msg import Header
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import numpy as np
import matplotlib.pyplot as plt
from collections import deque

class LatencySubscriberPlot(Node):
    def __init__(self):
        super().__init__('latency_subscriber_plot')

        # Parámetro de fiabilidad
        self.declare_parameter('reliability', 'reliable')  # reliable | best_effort
        reliability_str = self.get_parameter('reliability').get_parameter_value().string_value
        reliability = ReliabilityPolicy.RELIABLE if reliability_str == 'reliable' else ReliabilityPolicy.BEST_EFFORT

        qos_profile = QoSProfile(
            reliability=reliability,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Subscripción al tópico
        self.subscription = self.create_subscription(
            Header,
            'latency_topic',
            self.listener_callback,
            qos_profile
        )

        # Buffers circulares para graficar
        self.lat_buffer = deque(maxlen=200)
        self.jitter_buffer = deque(maxlen=200)
        self.last_latency = None
        self.count = 0

        # Configura el gráfico
        plt.ion()
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(8, 6))
        self.line1, = self.ax1.plot([], [], label='Latency (ms)')
        self.line2, = self.ax2.plot([], [], color='orange', label='Jitter (ms)')
        self.ax1.set_ylabel('Latency [ms]')
        self.ax2.set_ylabel('Jitter [ms]')
        self.ax2.set_xlabel('Samples')
        self.ax1.grid(True)
        self.ax2.grid(True)
        self.ax1.legend()
        self.ax2.legend()

        self.get_logger().info(f'Subscriber with live plot started ({reliability_str.upper()})')

    def listener_callback(self, msg):
        now = self.get_clock().now().nanoseconds / 1e9
        sent_time = msg.stamp.sec + msg.stamp.nanosec / 1e9
        latency = (now - sent_time) * 1000.0  # en ms
        jitter = abs(latency - self.last_latency) if self.last_latency is not None else 0.0
        self.last_latency = latency

        self.lat_buffer.append(latency)
        self.jitter_buffer.append(jitter)
        self.count += 1

        if self.count % 5 == 0:  # refresca el gráfico cada 5 muestras
            self.update_plot()

    def update_plot(self):
        x = np.arange(len(self.lat_buffer))
        self.line1.set_data(x, list(self.lat_buffer))
        self.ax1.relim()
        self.ax1.autoscale_view()

        self.line2.set_data(x, list(self.jitter_buffer))
        self.ax2.relim()
        self.ax2.autoscale_view()

        plt.pause(0.001)

def main(args=None):
    rclpy.init(args=args)
    node = LatencySubscriberPlot()

    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        plt.ioff()
        plt.show()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
