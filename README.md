# ROS 2 Latency Evaluation Methodology

This section describes the general methodology used to evaluate and compare the performance of different ROS 2 Middlewares (RMW) (CycloneDDS, FastDDS, Zenoh).

## Experimental Setup

The experiment is based on a **Publisher-Subscriber** (or Ping-Pong) communication pattern designed to measure message transit time.

### Data Flow
1. **Publisher (Sender):** Periodically publishes messages at a fixed frequency.
2. **Payload:** Each message contains a *timestamp* recording the exact instant of transmission.
3. **Subscriber (Receiver):** Receives the message, records the arrival time, and calculates instantaneous latency.
---

## Experimental Conditions

To ensure **reproducibility** and a fair comparison, the following conditions are strictly maintained across all benchmarks:

| Parameter | Value / Condition | Note |
| :--- | :--- | :--- |
| **Hardware / Network** | Same network and containerized environment for all tests. |
| **Frequency** | 20 Hz | Constant publication rate. |
| **Message Size** | Simple structure | `std_msgs/Header`. |
| **Duration** | 60 seconds | Fixed duration per test run. |
| **Warm-up** | 15 samples | Initial samples are discarded from metric calculations to eliminate startup spikes. |
---

## Metrics Computed

For each evaluated middleware, the system collects and computes the following statistics:

* **Mean Latency:** Arithmetic average across all received messages.
* **Minimum and Maximum Latency:** Used to identify network peaks and latency outliers.
* **Jitter (Variability):** Mean standard deviation of latency (communication stability).
* **Maximum Jitter:** Used to identify network spikes.
---

## Running the Tests

To replicate the experiment, follow these steps for each ROS 2 middleware:

1. **Configure ROS 2 Middleware:**
    ```bash
    # Example for CycloneDDS
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    ```
2. **Start Subscriber (Listener):**
    ```bash
    python3 subscriber_latency
    ```
3. **Start Router in Zenoh:**
    ```bash
    ros2 run rmw_zenoh_cpp rmw_zenohd
    ```
4. **Start Publisher (Talker):**
    ```bash
    python3 publisher_latency
    ```
5. **Command to Verify Active Middleware:**
    ```bash
    ros2 doctor --report | grep middleware
    ```
6. **Data Collection:** The script automatically records samples for 60 seconds and saves them to a `csv` file.
---

## Results Structure

Data is automatically saved to CSV files with the following format:

| samples | latency | jitter | timestamp_s

## Experimental Results: Middleware Comparison

Below are the results obtained after running latency benchmarks at a 20 Hz frequency for 60 seconds.

**Units:** Milliseconds (ms)

| Middleware | Mean Latency | Min Lat. | Max Lat. | Mean Jitter | Max Jitter | Sample Count |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Fast DDS** | 0.972 ms | 0.547 | 1.647 | 0.119 | 0.796 | 1180 |
| **Cyclone DDS** | **0.867 ms** | **0.424** | **1.281** | **0.099** | 0.640 | 1181 |
| **Zenoh** | 1.216 ms | 0.750 | 1.736 | 0.103 | **0.555** | 1180 |
| **Fast DDS** (QoS) | 0.805 ms | 0.259 | 1.727 | 0.136 | 1.127 | 1181 |
| **Cyclone** (QoS) | **0.755 ms** | **0.255** | **1.186** | **0.129** | **0.578** | 1181 | 
| **Zenoh** (QoS) | 1.725 ms | 0.588 | 3.421 | 0.556 | 1.887 | 1153 | 

## Analysis of Results

### Latency and Jitter

1. **Fast DDS (Default vs. QoS):** In its default configuration, Fast DDS exhibits an **extreme initial spike of 217 ms** (likely during initial peer discovery), which required a significant warm-up threshold to prevent metrics distortion. It is the second-best middleware in terms of average latency and the worst in terms of average jitter. When applying optimized QoS, peak latencies drop drastically (even those outside the warm-up window), and both average latency and jitter decrease slightly.
2. **Cyclone DDS (Consistency):** Shows the best overall performance in both scenarios. It is the winner in both mean latency and mean jitter across configurations, with minimal spikes, demonstrating very low computational overhead.
3. **Zenoh (Trade-off):** In standard mode, its jitter is marginally higher than Cyclone's, while its mean latency is ~0.35 ms higher due to the routing hop through the Router. Notably, its maximum jitter is the lowest among all three. Interestingly, the applied QoS configuration degraded performance, increasing both latency and variability.

### Temporal Stability

![alt text](latency_DDS_Zenoh/latency_test_py/results/no_qos_latency_timeseries.png)

1. **Cyclone DDS:** Consistently stays within the lower band with very low oscillation amplitude.

2. **Fast DDS:** Shows intermediate behavior. While stable, its signal is noticeably "noisier" than Cyclone's, oscillating frequently.

3. **Zenoh:** Demonstrates very uniform behavior. The green band runs parallel to the others, confirming that its additional latency is a fixed, predictable cost (Router).

![alt text](latency_DDS_Zenoh/latency_test_py/results/no_qos_jitter_timeseries.png)

1. **Cyclone DDS:** Exhibits the best baseline stability. The vast majority of its values stay anchored near the 0.0 axis.

2. **Fast DDS:** Displays the greatest temporal instability. Multiple recurrent, sharp spikes are observed, indicating unpredictable variance in message arrival times.

3. **Zenoh:** Demonstrates consistent, bounded stability. Although its baseline "noise" level is slightly higher than Cyclone's (denser in the 0.1–0.3 ms range), it does not suffer from the extreme spikes seen in Fast DDS. It almost always stays below 0.5 ms, indicating highly predictable and bounded behavior that effectively avoids extreme latency peaks.

![alt text](latency_DDS_Zenoh/latency_test_py/results/with_qos_latency_timeseries.png)

1. **Cyclone DDS QoS:** Maintains total dominance. The signal is extremely compact and low, fluctuating minimally between 0.5 ms and 0.9 ms.
2. **Fast DDS QoS:** Unlike its default version, here it closely tracks Cyclone, eliminating nearly all noise and dramatically improving its temporal stability.
3. **Zenoh QoS:** Suffers a severe regression in stability. The plot shows chaotic, wide-amplitude oscillations (between 1.0 ms and 3.5 ms), indicating that the chosen QoS policy caused router saturation, losing all the predictability of its default version.

![alt text](latency_DDS_Zenoh/latency_test_py/results/with_qos_jitter_timeseries.png)

1. **Cyclone DDS QoS:** Its line remains consistently pinned to the X-axis (0.0 ms), with almost no significant deviations.
2. **Fast DDS QoS:** Unlike its default version, here it tracks Cyclone almost perfectly near the bottom of the plot. The QoS policy eliminated the earlier noise, making it as stable as Cyclone in this benchmark.
3. **Zenoh QoS:** The plot is dominated by frequent, sharp spikes reaching up to 1.8 ms. Visually, it is the noisiest line.

### Configuration Complexity

1. **Cyclone DDS (Low):** Requires no external XML files or daemons to deliver the best benchmark results.
2. **Zenoh (Medium-High):** Requires running `rmw_zenohd` (Router) as a separate daemon. Furthermore, as the benchmark graphs illustrate, tuning its QoS is non-trivial and can degrade performance if not properly configured.
3. **Fast DDS (Medium):** Works adequately by default, but requires custom XML configuration files to unlock its full potential and avoid discovery latency spikes.

### Suitability for Robotic Scenarios

| Scenario | Recommendation | Rationale |
| :--- | :--- | :--- |
| **Real-Time Control** (Motors, PID) | **Cyclone DDS** | Minimal latency (<1 ms) and near-zero jitter are critical to avoid control loop oscillations. |
| **Monitoring / Sensors** (LiDAR, Cameras) | **Fast DDS** | Once properly configured with QoS, it efficiently manages high bandwidth. |
| **Edge-Cloud / Fleets / Wi-Fi** | **Zenoh** | Despite slightly higher latency, its routed architecture is uniquely designed to traverse the Internet and scale across multi-robot fleets without saturating wireless networks. |

### Sample Count Analysis
The theoretical experiment (20 Hz * 60 s) should yield **1200 samples**. The test protocol discards the **first 15 samples** as a *warm-up*, leaving an **ideal maximum of 1185 samples**.

* **High Reliability (DDS):** Both Fast DDS and Cyclone DDS, across both configurations, recorded between **1180 and 1181 samples**. The minor discrepancy of ~4–5 messages compared to the theoretical ideal is typically due to node teardown latency when reaching the exact elapsed time, representing negligible message loss.
* **Packet Loss in Zenoh QoS:** The case of Zenoh (QoS) with **1153 samples** is significant. It falls short by ~35 messages relative to the ideal, representing an **actual packet loss rate of 2.95%**.

