import rclpy
from rclpy.node import Node
from std_msgs.msg import Header
import numpy as np
import os
import csv

class LatencySubscriber(Node):
    def __init__(self, csv_path='latency_stats.csv', max_duration=60.0):
        super().__init__('latency_subscriber')
        self.subscription = self.create_subscription(
            Header,
            'latency_topic',
            self.listener_callback,
            10)
        self.latencies = []
        self.last_latency = None
        self.csv_path = csv_path
        self.start_time = self.get_clock().now().nanoseconds / 1e9
        self.max_duration = max_duration
        self.stopped = False
        self.get_logger().info('Latency subscriber started')

    def listener_callback(self, msg):
        if self.stopped:
            return

        # Calcula el tiempo actual y la latencia
        now = self.get_clock().now().nanoseconds / 1e9
        elapsed = now - self.start_time
        sent_time = msg.stamp.sec + msg.stamp.nanosec / 1e9
        latency = now - sent_time
        self.latencies.append(latency)

        # Calcula el jitter como la variación absoluta entre latencias consecutivas
        if self.last_latency is not None:
            jitter = abs(latency - self.last_latency)
        else:
            jitter = 0.0
        self.last_latency = latency

        # Muestra por pantalla
        self.get_logger().info(
            f'Latency: {latency*1000:.3f} ms | Jitter: {jitter*1000:.3f} ms | Samples: {len(self.latencies)}'
        )

        # Cada 100 muestras, muestra estadísticas
        if len(self.latencies) % 100 == 0:
            lat_arr = np.array(self.latencies)
            avg = np.mean(lat_arr) * 1000
            std = np.std(lat_arr) * 1000
            self.get_logger().info(f'--- Average latency: {avg:.3f} ms | Jitter std dev: {std:.3f} ms ---')

        file_exists = os.path.exists(self.csv_path)
        try:
            with open(self.csv_path, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(['samples', 'latency', 'jitter', 'timestamp_s'])
                writer.writerow([len(self.latencies), f'{self.last_latency*1000:.3f}', f'{jitter*1000:.3f}', f'{now:.6f}'])
        except Exception as e:
            self.get_logger().error(f'Failed writing CSV: {e}')

        # Detener experimento después de max_duration segundos
        if elapsed >= self.max_duration:
            self.get_logger().info(f'Max duration {self.max_duration}s reached ({elapsed:.3f}s). Stopping.')
            self.stopped = True
            rclpy.shutdown()
    

def main(args=None):
    rclpy.init(args=args)
    node = LatencySubscriber(csv_path='./latency_stats.csv', max_duration=60.0)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        rclpy.shutdown()

if __name__ == '__main__':
    main()
