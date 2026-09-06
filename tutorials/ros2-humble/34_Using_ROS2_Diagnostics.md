# Chapter 21. Using_ROS2_Diagnostics

[← Back to Contents](00_Contents.md) | [← Previous: Chapter 20 — Understanding ROS2 Diagnostics](33_Understanding_ROS2_Diagnostics.md) | [Next: Chapter 22 — ROS2 Diagnostics Use Example →](35_ROS2_Diagnostics_Use_Example.md)

---

# README 2: Using ROS 2 Diagnostics

In the previous chapter, we explored the theory and architecture of the ROS 2 Diagnostics framework. Now, we move from theory to implementation.

This chapter is designed to be a practical guide for developers. We will provide standardized C++ boilerplate templates that you can integrate into your own nodes. These templates leverage the official `diagnostic_updater` library to monitor the most common communication patterns in ROS 2: Topics, Services, and Actions.

## Goal of this Chapter

By the end of this guide, you will be able to:

- **Monitor Performance**: Automatically track if your topics are publishing at the correct rates or if your services are failing.
- **Organize Health Data**: Use the Aggregator to sort raw data into a structured system health dashboard.
- **Visualize Status**: Use the rqt_robot_monitor to identify and troubleshoot issues in real-time.

## How to use the Boilerplates

Each code example is annotated with descriptive comments to help you distinguish between the framework requirements and your specific application logic:

- **Mandatory Diagnostic Setup**: These sections are required for the ROS 2 diagnostic pipeline to function. They handle the initialization of the Updater and the background publishing of messages.
- **User-Defined Logic**: This is where you insert your specific hardware or software check logics. You have full control over the thresholds (e.g., what temperature is too high?) and the error messages sent to the operator.

## 1. Using ROS 2 Diagnostics for Monitoring a Topic

To monitor a topic effectively, you don’t need to write manual “if-else” logic to calculate time intervals or check message rates. The `diagnostic_updater` package provides the `DiagnosedPublisher` class, which handles frequency and latency tracking automatically.

### C++ Boilerplate Template: Topic Monitoring

```cpp
#include<rclcpp/rclcpp.hpp>
#include<std_msgs/msg/string.hpp>

// --- MANDATORY: Include the diagnostic updater headers ---
#include<diagnostic_updater/diagnostic_updater.hpp>
#include<diagnostic_updater/publisher.hpp>

class TopicMonitorNode : public rclcpp::Node
{
public:
    TopicMonitorNode() : Node("topic_monitor_node")
    {
        // --- MANDATORY DIAGNOSTIC SETUP ---

        // 1. Initialize the Updater and set a Hardware ID
        // The Hardware ID is crucial for the Aggregator to identify this specific component.
        // You can set Hardware ID "string" as per your own needs.
        updater_.setHardwareID("generic_sensor_001");

        // 2. Define the expected performance parameters
        double min_freq = 9.0;
        double max_freq = 11.0;

        // FrequencyStatusParam(min, max, error_tolerance, window_size)
        diagnostic_updater::FrequencyStatusParam freq_param(&min_freq, &max_freq, 0.1, 10);

        // Timestamp: We expect the message header time to be within 0.1s of current time.
        // TimeStampStatusParam(min_acceptable_delay, max_acceptable_delay)
        diagnostic_updater::TimeStampStatusParam time_param(-0.1, 0.1);

        // 3. Create the DiagnosedPublisher
        // This replaces a standard 'create_publisher' call.
        // It wraps the publisher and automatically reports health to the /diagnostics topic.
        // Change `"example_topic"` to your actual data topic name.
        diagnosed_pub_ = std::make_shared<diagnostic_updater::DiagnosedPublisher<std_msgs::msg::String>>(
            this->create_publisher<std_msgs/msg::String>("example_topic", 10),
            updater_,
            freq_param,
            time_param
        );

        // Timer to simulate data publishing
        timer_ = this->create_wall_timer(
            std::chrono::milliseconds(100),
            std::bind(&TopicMonitorNode::publish_data, this)
        );
    }

private:
    void publish_data()
    {
        auto message = std_msgs::msg::String();

        // --- USER LOGIC PART: START ---
        // Example: Simulated Sensor Reading (e.g., Temperature)
        double current_temp = 45.0; // In a real node, this comes from hardware
        double temp_limit_warn = 70.0;
        double temp_limit_error = 90.0;

        if (current_temp >= temp_limit_error) {
            // Logically, you might stop the robot here
            message.data = "CRITICAL: OVERHEAT";
            // Note: The DiagnosedPublisher handles Frequency/Timestamp,
            // but you can add custom text to your messages here.
        }
        else if (current_temp >= temp_limit_warn) {
            message.data = "WARNING: HIGH TEMP";
        }
        else {
            message.data = "Temperature OK";
        }
        // --- USER LOGIC PART:END ---

        // The DiagnosedPublisher works exactly like a regular publisher.
        // However, every call to 'publish' updates the frequency statistics internally.
        diagnosed_pub_->publish(message);

        // --- MANDATORY DIAGNOSTIC UPDATE ---
        // The updater must be called periodically to process the data and publish to /diagnostics.
        updater_.update();
    }

    // Diagnostics Members
    diagnostic_updater::Updater updater_{this};
    std::shared_ptr<diagnostic_updater::DiagnosedPublisher<std_msgs::msg::String>> diagnosed_pub_;
    rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<TopicMonitorNode>());
    rclcpp::shutdown();
    return 0;
}
```

### How this Code Works

- **`diagnostic_updater::Updater`**: The central object that manages all diagnostic tasks within this node. It acts as the “orchestrator” that gathers information from all registered tasks and bundles them for publication.
- **`FrequencyStatusParam(&min, &max, tolerance, window)`**:
    - **Tolerance (0.1)**: This is the tolerance percentage (expressed as a decimal) allowed before the status level changes. It prevents the diagnostics from “flickering” between OK and WARN if the frequency dips just a tiny bit below your `min_freq`. With min_freq = 9.0 and a tolerance of 0.1 (10%), the status will only turn to WARN if the frequency drops below 9.0−(9.0×0.1)=8.1 Hz.
    - **Window (10)**: The number of messages to average. A window of 10 means the frequency is calculated over the last 10 messages, making the report smoother and less jumpy.
- **`TimeStampStatusParam(min, max)`**: This monitors “Latency” (data freshness) rather than frequency. It compares the **System Clock** (now) to the **Message Header Stamp** (when data was created).
    - **Max Delay (0.1)**: Catches **Lag**. If the message header says “T=0” but the receiver’s clock says “T=0.2”, the delay is 0.2. Since 0.2 > 0.1, it triggers a warning.
    - **Min Delay (-0.1)**: Catches **Clock Sync Issues**. If the message header says “T=0.5” but the receiver’s clock only says “T=0.4”, it looks like the message came from the future! This usually happens if two computers on a network have clocks that aren’t synchronized.
- **`diagnosed_pub_->publish()`**: This is a “drop-in” replacement for the standard ROS 2 publish call. It automatically tracks every message sent to update the frequency and timestamp statistics.

### Key Customization Points

- **Hardware ID**: Update `"generic_sensor_001"` to reflect your specific hardware.
- **Frequency Limits**: Adjust `min_freq` and `max_freq` based on your sensor’s expected output.
- **Time Limits**: If you are on a slow network (like long-range Wi-Fi), you may need to increase the Max Delay (e.g., to `0.5`) to avoid constant lag warnings.

## 2. Using ROS 2 Diagnostics for Monitoring a Service

When monitoring a service, we typically want to report the performance and reliability of the last call. Unlike topics, services are asynchronous and event-driven, so we create a custom callback function that the `Updater` runs to check the service’s internal “health variables.”

### C++ Boilerplate Template: Service Monitoring

```cpp
#include<rclcpp/rclcpp.hpp>
// [USER-MODIFIABLE]: Replace with your specific service interface
#include<example_interfaces/srv/add_two_ints.hpp>

// [MANDATORY]: Include the diagnostic updater header
#include<diagnostic_updater/diagnostic_updater.hpp>

class ServiceMonitorNode : public rclcpp::Node
{
public:
    // [USER-MODIFIABLE]: Rename the node as needed
    ServiceMonitorNode() : Node("service_monitor_node")
    {
        // --- MANDATORY DIAGNOSTIC SETUP ---

        // 1. [USER-MODIFIABLE]: Set a unique Hardware ID for this component
        updater_.setHardwareID("computation_engine_v1");

        // 2. [MANDATORY]: Register a diagnostic task.
        // "Service Health Check" is the [USER-MODIFIABLE] label seen in the GUI.
        updater_.add("Service Health Check", this, &ServiceMonitorNode::check_service_health);

        // [USER-MODIFIABLE]: Standard service server creation
        // [USER-MODIFIABLE]: Update service interface and service name to match your requirements
        service_ = this->create_service<example_interfaces::srv::AddTwoInts>(
            "add_two_ints",
            std::bind(&ServiceMonitorNode::handle_service, this, std::placeholders::_1, std::placeholders::_2)
        );
    }

private:
    // --- USER LOGIC: SERVICE HANDLER ---
    void handle_service(
        // [USER-MODIFIABLE]: Update service interface to match your requirements
        const std::shared_ptr<example_interfaces::srv::AddTwoInts::Request> request,
        std::shared_ptr<example_interfaces::srv::AddTwoInts::Response> response)
    {
        // Start timer to measure performance
        auto start_time = this->now();

        // [USER-MODIFIABLE]: Perform your actual service/business logic
        response->sum = request->a + request->b;

        // --- Record metrics for the diagnostic report ---
        auto end_time = this->now();
        last_execution_time_ = (end_time - start_time).seconds();
        call_count_++;

        // [MANDATORY]: Trigger the updater to run the registered tasks
        // and publish the results to /diagnostics immediately.
        updater_.update();
    }

    // --- USER LOGIC: DIAGNOSTIC CALLBACK ---
    // [MANDATORY]: This callback function is used by the updater
    void check_service_health(diagnostic_updater::DiagnosticStatusWrapper &stat)
    {
        // [USER-MODIFIABLE]: Define logic and thresholds (e.g., 0.5s)
        if (last_execution_time_ > 0.5) {
            stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Service is slow");
        } else if (call_count_ == 0) {
            stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Waiting for first call");
        } else {
            stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Service responding normally");
        }

        // [USER-MODIFIABLE]: Add custom data rows for the GUI
        stat.add("Last Execution Time (s)", last_execution_time_);
        stat.add("Total Calls Received", call_count_);
    }

    // Members
    // [USER-MODIFIABLE]: Update type to match your service interface
    rclcpp::Service<example_interfaces::srv::AddTwoInts>::SharedPtr service_;

    // [MANDATORY]: The diagnostic updater object
    diagnostic_updater::Updater updater_{this};

    // [USER-MODIFIABLE]: Variables to hold state for the diagnostic report
    double last_execution_time_ = 0.0;
    int call_count_ = 0;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ServiceMonitorNode>());
    rclcpp::shutdown();
    return 0;
}
```

### How this Code Works

- **`updater_.update()`** **(The Trigger)**: This is vital. In a service-based node, the node is often idle. Calling update() inside the handler ensures that as soon as the service finishes, the new performance data is published to the system. Without this, the diagnostics would only update on a slow, fixed background timer.
- **`updater_.add("Name", callback)`**: This is the manual way to register a diagnostic task. Every time `updater_.update()` is called, it triggers this function to evaluate the current health of the service.
- **`check_service_health` (The Callback)**: This function is the “Logic Core.” Its role is to translate your raw variables (like execution time) into a human-readable status (OK/WARN/ERROR). It doesn’t run constantly; it only runs when triggered by the `Updater`.
- **The Diagnostic Pipeline**:
    1. The **Service Handler** records the raw performance data.
    2. **`updater_.update()`** calls the callback function that was previously registered by add() `updater_.add()` i.e. the `check_service_health` callback function.
    3. The **Callback** (`check_service_health`) is executed to evaluate that data against your thresholds. It compares your raw numbers against your thresholds (e.g., “Is 0.6s > 0.5s?”) and sets the severity level **(OK/WARN/ERROR)**.
    4. The **Updater** packages the result into a `DiagnosticArray` and publishes it.
- **`DiagnosticStatusWrapper &stat`**: This object is the “Report Builder” used to construct the diagnostic message.
- **`stat.summary(level, "message")`**: Sets the overall severity (OK/WARN/ERROR) and a short descriptive string for the user.
- **`stat.add("Key", value)`**: Appends detailed data points (e.g., specific numbers or strings) that an operator can inspect in the `rqt_robot_monitor`.
- **Execution Timing**: By measuring the difference between `start_time` and `end_time`, we can detect if a service (like a complex planner) is starting to lag or become a bottleneck in the system.

### Key Customization Points

- **Thresholds**: Change `0.5` seconds to a value appropriate for your task. A heavy pathfinding service might allow `2.0s`, while a hardware toggle should be nearly instant (`0.01s`).
- **Success Tracking**: You can expand the logic to include `try-catch` blocks. If the service fails to compute a result, you can use the diagnostic callback to set the status to **ERROR**.
- **Call Frequency**: If a service that should be called once per second hasn’t been called in a minute, you could trigger a **WARN** in the diagnostic logic to indicate a lost connection or an idle upstream node.

## 3. Using ROS 2 Diagnostics for Monitoring an Action

Monitoring an **Action** is more involved than a Service because Actions are long-running and provide continuous **Feedback**. We don’t just care about the final result; we need to know if the action is progressing or if it has “frozen” during execution.

### C++ Boilerplate Template: Action Monitoring

```cpp
#include<rclcpp/rclcpp.hpp>
#include<rclcpp_action/rclcpp_action.hpp>

// [USER-MODIFIABLE]: Replace with your specific action interface
#include<example_interfaces/action/fibonacci.hpp>

// [MANDATORY]: Include the diagnostic updater header
#include<diagnostic_updater/diagnostic_updater.hpp>

class ActionMonitorNode : public rclcpp::Node
{
public:
    using Fibonacci = example_interfaces::action::Fibonacci;
    using GoalHandleFibonacci = rclcpp_action::ServerGoalHandle<Fibonacci>;

    ActionMonitorNode() : Node("action_monitor_node")
    {
        // --- MANDATORY DIAGNOSTIC SETUP ---

        // 1. [USER-MODIFIABLE]: Set a unique Hardware ID
        updater_.setHardwareID("action_engine_v1");

        // 2. [MANDATORY]: Register the diagnostic task
        updater_.add("Action Health Check", this, &ActionMonitorNode::check_action_health);

        // [USER-MODIFIABLE]: Standard Action Server creation
        this->action_server_ = rclcpp_action::create_server<Fibonacci>(
            this, "fibonacci",
            std::bind(&ActionMonitorNode::handle_goal, this, std::placeholders::_1, std::placeholders::_2),
            std::bind(&ActionMonitorNode::handle_cancel, this, std::placeholders::_1),
            std::bind(&ActionMonitorNode::handle_accepted, this, std::placeholders::_1));
    }

private:
    // --- USER LOGIC: ACTION HANDLERS ---
    rclcpp_action::GoalResponse handle_goal(
        const rclcpp_action::GoalUUID & uuid,
        std::shared_ptr<const Fibonacci::Goal> goal)
    {
        (void)uuid;
        return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;
    }

    rclcpp_action::CancelResponse handle_cancel(const std::shared_ptr<GoalHandleFibonacci> goal_handle)
    {
        (void)goal_handle;
        return rclcpp_action::CancelResponse::ACCEPT;
    }

    void handle_accepted(const std::shared_ptr<GoalHandleFibonacci> goal_handle)
    {
        // [MANDATORY]: Execute in a separate thread to prevent blocking
        std::thread{std::bind(&ActionMonitorNode::execute, this, std::placeholders::_1), goal_handle}.detach();
    }

    void execute(const std::shared_ptr<GoalHandleFibonacci> goal_handle)
    {
        const auto goal = goal_handle->get_goal();
        auto feedback = std::make_shared<Fibonacci::Feedback>();
        auto result = std::make_shared<Fibonacci::Result>();

        // Initialize health tracking variables
        start_time_ = this->now();
        is_active_ = true;

        for (int i = 1; (i < goal->order) && rclcpp::ok(); ++i) {
            if (goal_handle->is_canceling()) {
                is_active_ = false;
                goal_handle->canceled(result);
                return;
            }

            // [USER-MODIFIABLE]: Perform task logic
            feedback->sequence.push_back(i);
            goal_handle->publish_feedback(feedback);

            // --- Record feedback time for diagnostics ---
            last_feedback_time_ = this->now();

            // [MANDATORY]: Trigger diagnostics during the loop so
            // the GUI updates while the action is still running.
            updater_.update();

            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }

        // Action finished
        is_active_ = false;
        if (rclcpp::ok()) {
            goal_handle->succeed(result);
            updater_.update();
        }
    }

    // --- USER LOGIC: DIAGNOSTIC CALLBACK ---
    void check_action_health(diagnostic_updater::DiagnosticStatusWrapper &stat)
    {
        if (!is_active_) {
            stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Action Server Idle");
        } else {
            // [USER-MODIFIABLE]: Define logic for "Stale" feedback or timeouts
            double time_since_feedback = (this->now() - last_feedback_time_).seconds();
            double total_duration = (this->now() - start_time_).seconds();

            if (time_since_feedback > 2.0) {
                stat.summary(diagnostic_msgs::msg::DiagnosticStatus::ERROR, "Action Frozen: No Feedback");
            } else if (total_duration > 30.0) {
                stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Action taking too long");
            } else {
                stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Action progressing");
            }

            // [USER-MODIFIABLE]: Add metrics to the diagnostic report
            stat.add("Time since last feedback (s)", time_since_feedback);
            stat.add("Total execution time (s)", total_duration);
        }
    }

    // Members
    rclcpp_action::Server<Fibonacci>::SharedPtr action_server_;

    // [MANDATORY]: The diagnostic updater
    diagnostic_updater::Updater updater_{this};

    // [USER-MODIFIABLE]: State variables for health report
    rclcpp::Time start_time_;
    rclcpp::Time last_feedback_time_;
    bool is_active_ = false;
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ActionMonitorNode>());
    rclcpp::shutdown();
    return 0;
}
```

### How this Code Works

- **Long-Running Tracking**: Because an Action can run for seconds or minutes, we call `updater_.update()` inside the execution loop (the `for` loop). This ensures that the `/diagnostics` topic is updated continuously, allowing the “Total execution time” to grow in real-time on the monitoring dashboard.
- **Stale Feedback Detection**: We record `last_feedback_time_` every time the action sends a feedback update to the client. If the internal logic gets stuck in a heavy calculation or a hardware hang occurs, the feedback stops. The Diagnostic Callback will detect this time gap and report an **ERROR**.
- **Active vs. Idle**: The logic uses a boolean flag (`is_active_`) to distinguish between the server being “Idle” (ready for a goal) and “Processing” (currently executing). This prevents false warnings about “Total execution time” when the robot is simply waiting for a command.

### Key Customization Points

- **Action Interface**: You **must** change the `#include` and the `using` aliases (e.g., `using Fibonacci = ...`) to match the specific `.action` file used in your project.
- **Timeouts**:
    - **Stale Feedback (2.0s)**: Adjust this based on your feedback rate. If your action provides feedback at 10Hz, a 2-second gap is a major error. If it provides feedback every 5 seconds, this limit should be increased to something like `10.0`.
    - **Total Duration (30.0s)**: Set this to the maximum “sane” limit for the task. For example, a robot navigating to a nearby room might have a limit of `120.0` seconds.
- **Hardware ID**: Update `"action_engine_v1"` to a unique string identifying the specific subsystem (e.g., `navigation_action` or `manipulator_controller`).

## 4. Using Prebuilt codes from `diagnostics_common_diagnostics` package

The **`ros/diagnostics`** library provides the **`diagnostics_common_diagnostics`** package, which contains pre-made nodes for monitoring “generic” hardware and system health. These are highly optimized and adhere to the standard diagnostic format, making them instantly compatible with the Aggregator and Robot’s Hardware.

### List of Prebuilt Monitor codes provided by the `diagnostics_common_diagnostics` package

The `diagnostics_common_diagnostics` package provides several specialized monitoring nodes. Instead of writing custom C++ code, you can use these ready-made codes to monitor standard system metrics:

| Module Name | Purpose |
| --- | --- |
| **`cpu_monitor.py`** | Allows users to monitor the CPU usage of their system in real-time. It publishes the usage percentage in a diagnostic message. |
| **`ntp_monitor.py`** | Checks if the system clock is synchronized with a network time protocol (NTP) server (critical for multi-robot setups). |
| **`hd_monitor.py`** | Monitors hard drive temperature and remaining disk space. |
| **`ram_monitor.py`** | Allows users to monitor the RAM usage of their system in real-time. It publishes the usage percentage in a diagnostic message. |
| **`sensors_monitor.py`** | Allows users to monitor the temperature, volt and fan speeds of any system sensor/hardware system in real-time. It uses the `LM_Sensors` package to get the data. |

If you wish to study these source codes, they can be directly accessed at the folowing official address: https://github.com/ros/diagnostics/tree/ros2/diagnostic_common_diagnostics/diagnostic_common_diagnostics

### How to use them

Since these monitors are external components, you must first configure your package to recognize them as dependencies before you can use them in a launch file.

### Step 1: Configuration (Package Setup)

**System Installation**: If you are working on a new machine, ensure the package is installed via terminal:

```bash
sudo apt install ros-<ros2-distro>-diagnostics-common-diagnostics
```

Update your project’s configuration files to ensure the `diagnostics_common_diagnostics` package is included during the build and install process.

**In your `package.xml`:**

```xml
<depend>diagnostics_common_diagnostics</depend>
```

**In your `CMakeLists.txt`:**

```
find_package(diagnostics_common_diagnostics REQUIRED)
```

### Step 2: Implementation (Launch File)

Because these are prebuilt, you do not need to write any custom source code. You simply “summon” them inside your Python launch file as you would with any other node.

**Example launch file code that lauches all the modules provided by the `diagnostics_common_diagnostics` package**

```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([

        # 1. CPU MONITOR
        # Monitors total CPU usage to detect processing bottlenecks.
        Node(
            package='diagnostics_common_diagnostics',
            executable='cpu_monitor.py',
            name='cpu_monitor',
            parameters=[{
                'warning_percentage': 85,  # Threshold: If total CPU usage > 85%, status becomes WARN.
                'window': 5                # Smoothing: Averages usage over the last 5 readings to filter out brief spikes.
            }]
        ),

        # 2. RAM MONITOR
        # Monitors memory usage to detect memory leaks or high-load conditions.
        Node(
            package='diagnostics_common_diagnostics',
            executable='ram_monitor.py',
            name='ram_monitor',
            parameters=[{
                'warning_percentage': 80,  # Threshold: If RAM usage > 80%, status becomes WARN.
                'window': 3                # Smoothing: Averages usage over the last 3 readings to prevent flickering alerts.
            }]
        ),

        # 3. HD (Hard Drive) MONITOR
        # Ensures the system has enough disk space for logs, maps, and recordings.
        Node(
            package='diagnostics_common_diagnostics',
            executable='hd_monitor.py',
            name='hd_monitor',
            parameters=[{
                'path': '/',                 # Location: The disk partition/mount point to monitor (usually '/' for root).
                'free_percent_low': 10.0,    # Warning: Triggered when free space drops below 10%.
                'free_percent_crit': 5.0     # Critical: Triggered when free space drops below 5% (risk of system crash).
            }]
        ),

        # 4. NTP MONITOR
        # Crucial for multi-computer setups to ensure message timestamps are synchronized.
        Node(
            package='diagnostics_common_diagnostics',
            executable='ntp_monitor.py',
            name='ntp_monitor',
            parameters=[{
                'ntp_hostname': 'pool.ntp.org',     # Server: The NTP server used to check the local clock's accuracy.
                'offset-tolerance': 500.0,          # Warn: Max allowed clock drift in milliseconds before a Warning.
                'error-offset-tolerance': 5000.0,   # Error: Max allowed drift (5s) before a Critical Error.
                'diag-hostname': 'robot_base',      # Identity: The name of this computer as it appears in the diagnostic report.
                'self_offset-tolerance': 500.0,     # Sync: Tolerance for internal clock drift relative to its own measurements.
                'no-self-test': True                # Test: Disable/Enable the node's internal self-checks.
            }]
        ),

        # 5. SENSORS MONITOR
        # Monitors hardware health including motherboard temperatures, voltages, and cooling fans.
        Node(
            package='diagnostics_common_diagnostics',
            executable='sensors_monitor.py',
            name='sensors_monitor',
            parameters=[{
                'ignore_fans': False         # Toggle: Set to True if the robot is fanless or fan data is unreliable.
            }]
        )
    ])
```

Always make sure to configure the launch file by adding the following lines of code to your `CMakeLists.txt` file:

```
# Install Launch folder
install(
  DIRECTORY launch
  DESTINATION share/${PROJECT_NAME}
)
```

### Why use Prebuilt Codes?

- **Zero Coding**: No C++ required—just configuration.
- **Low Overhead**: These nodes are highly optimized to read system files (/proc, /sys) without slowing down your robot’s main processes.

## 5. Integrating Custom Diagnostics Node For Monitoring Network

Sometimes you need to monitor WiFi signal strength or internet latency metrics that the standard packages don’t cover. Below given is custom script for the exact same purpose.

### Step 1: Adding the Code

Create a folder named `scripts/` in your package’s root (at the same level as `src/` and `include/`) and paste the code there.

**`network_diagnostics.py`**

```python
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from diagnostic_updater import Updater, DiagnosticStatusWrapper
import socket
import os

class NetworkMonitor(Node):
    def __init__(self):
        super().__init__('network_monitor')

        # 1. Declare Parameters
        self.declare_parameter('ping_host', '8.8.8.8')
        self.declare_parameter('interface', 'xxxx')  # Change interface value 'xxxx' to match your system's network interface.
        self.declare_parameter('low_signal_threshold', -75)

        self.updater = Updater(self)
        self.updater.setHardwareID("Robot_Networking")
        self.updater.add("Wifi and Internet Status", self.check_network)

        self.get_logger().info("Network Monitor Node Started. Checking interface:%s" %
                               self.get_parameter('interface').value)

    def parameter_callback(self, params):
        """Logs changes made to parameters via CLI or other nodes."""
        for param in params:
            self.get_logger().info(f"Parameter '{param.name}' changed to:{param.value}")
        return SetParametersResult(successful=True)

    def get_wifi_signal(self):
        """Parses /proc/net/wireless to get dBm and Quality."""
        interface = self.get_parameter('interface').value
        try:
            with open("/proc/net/wireless", "r") as f:
                lines = f.readlines()
                for line in lines:
                    if interface in line:
                        parts = line.split()
                        # Index 2: Link Quality, Index 3: Signal level (dBm)
                        quality = float(parts[2].replace('.', ''))
                        level = float(parts[3].replace('.', ''))
                        return level, quality
        except Exception as e:
            self.get_logger().debug(f"Could not read wireless stats:{e}")
            return None, None
        return None, None

    def check_internet(self):
        """Checks internet connectivity via a socket connection to Port 53."""
        host = self.get_parameter('ping_host').value
        try:
            socket.setdefaulttimeout(1.5)
            # Use Port 53 (DNS) as it's almost always open
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 53))
            return True
        except (socket.error, socket.timeout):
            return False

    def check_network(self, stat: DiagnosticStatusWrapper):
        # ALWAYS fetch live values from parameters for testing
        low_signal_threshold = self.get_parameter('low_signal_threshold').value
        interface = self.get_parameter('interface').value

        level, quality = self.get_wifi_signal()
        internet_ok = self.check_internet()

        # --- Diagnostic Logic ---
        if level is None:
            stat.summary(stat.ERROR, f"WiFi Signal Not Found")
        elif not internet_ok:
            stat.summary(stat.WARN, "No Internet Access (Check Gateway/DNS)")
        elif level < low_signal_threshold:
            # This triggers if level is more negative than threshold (e.g., -80 < -75)
            stat.summary(stat.WARN, f"Weak WiFi Signal:{level} dBm")
        else:
            stat.summary(stat.OK, "Network Healthy")

        # --- Detailed Data Fields ---
        stat.add("Interface", interface)
        stat.add("Signal Level (dBm)", str(level) if level is not None else "N/A")
        stat.add("Link Quality", str(quality) if quality is not None else "N/A")
        stat.add("Internet Reachable", "Yes" if internet_ok else "No")
        stat.add("Ping Target", self.get_parameter('ping_host').value)
        stat.add("Current Threshold", str(low_signal_threshold))

        return stat

def main():
    rclpy.init()
    node = NetworkMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()

if __name__ == '__main__':
    main()
```

### Step 2: Configuration (Package Setup)

**Make the script executable**: Run this in your terminal inside the scripts/ folder:

```bash
chmod +x network_diagnostics.py
```

**Update CMakeLists.txt**: Add the following lines to install the script so ros2 run can find it:

```bash
find_package(rclpy REQUIRED)
find_package(diagnostic_updater REQUIRED)
find_package(diagnostic_msgs REQUIRED)

install(PROGRAMS
  scripts/network_diagnostics.py
  DESTINATION lib/${PROJECT_NAME}
)
```

**Update package.xml**: Ensure you have the necessary runtime dependencies:

```xml
<depend>rclpy</depend>
<depend>diagnostic_updater</depend>
<depend>diagnostic_msgs</depend>
```

### Step 3: Implementation in a Launch File

Now you can include your custom network monitor in your main launch file. Insert the following code in your launch file:

```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='your_package_name',
            executable='network_diagnostics.py',
            name='network_monitor_node',
            parameters=[{
                'ping_host': '8.8.8.8',
                'interface': 'xxxx',  # Change interface value 'xxxx' to match your system's network interface.
                'low_signal_threshold': -80
            }]
        ),

        # -------- Rest of your code  ----------
    ])
```

### How to find the interface name of your Local System ?

This is the standard Linux way to see every “doorway” (interface) on your machine, even if it’s currently turned off.

Run this command:

```bash
ip link show
```

Each entry starts with a number. Look for the line that starts with the word whose first letter is ‘w’ after the number. Copy that entire word and paste it in the `parameters::interface` field. That word is the interface name of your local system. Ex - `'wlp8s0'`

## 6. Implementing the Diagnostic Aggregator

The `diagnostic_aggregator` node acts as a filter and organizer. Instead of looking at a flat list of 50 different status messages, the operator sees a structured tree like **“Sensors”**, **“Compute”**, and **“Networking.”**

---

### Step 1: Create the Configuration (`.yaml`)

The aggregator is entirely driven by a configuration file. You define **“Analyzers”** that look for specific strings in the `hardware_id` or message fields of the diagnostic reports to group them.

**File Location:** `your_package_name/config/diagnostic_aggregator.yaml`

```yaml
/**:
ros__parameters:
analyzers:
      # --- GROUP 1: SYSTEM HEALTH ---
compute:
type: diagnostic_aggregator/AnalyzerGroup
path: Compute
analyzers:
cpu:
type: diagnostic_aggregator/GenericAnalyzer
path: CPU Usage
find_and_remove_prefix:'cpu_monitor'
ram:
type: diagnostic_aggregator/GenericAnalyzer
path: Memory
find_and_remove_prefix:'ram_monitor'

      # --- GROUP 2: NETWORKING ---
networking:
type: diagnostic_aggregator/GenericAnalyzer
path: Networking
        # This matches the Hardware ID we set in the Python script
hardware_id:'Robot_Networking'

      # --- GROUP 3: APPLICATION LOGIC (Topic/Service/Action) ---
application:
type: diagnostic_aggregator/AnalyzerGroup
path: App Logic
analyzers:
topics:
type: diagnostic_aggregator/GenericAnalyzer
path: Data Streams
            # Matches the name used in your Topic monitor
contains:'Topic Health'
services:
type: diagnostic_aggregator/GenericAnalyzer
path: Task Services
            # Matches the name used in your Service monitor
contains:'Service Health'
actions:
type: diagnostic_aggregator/GenericAnalyzer
path: Long Running Actions
            # Matches the name used in your Action monitor
contains:'Action Health Check'
```

Always make sure to register the `config` folder with your `CMakeLists.txt` file:

```
# Install Config folder
install(
  DIRECTORY config
  DESTINATION share/${PROJECT_NAME}
)
```

### Step 2: Implementation (Launch File)

You need to launch the aggregator node and point it to your YAML file so it knows how to categorize the incoming data.

```python
from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    # Get path to the yaml file
    config = os.path.join(
        get_package_share_directory('your_package_name'),
        'config',
        'diagnostic_aggregator.yaml'
    )

    return LaunchDescription([
        Node(
            package='diagnostic_aggregator',
            executable='aggregator_node',
            name='diagnostic_aggregator',
            parameters=[config]
        ),

        # ------ REST OF YOUR CODE ---------
    ])
```

### Step 3: Visualization with rqt_robot_monitor

Once the aggregator is running, it processes the raw `/diagnostics` and publishes a summarized, hierarchical topic called `/diagnostics_agg`. To view this structured data, run:

```bash
ros2 run rqt_robot_monitor rqt_robot_monitor
```

You can also add this node to your launch file:

```python
from launch import LaunchDescription
from launch_ros.actions import Node
import os
from ament_index_python.packages import get_package_share_directory
# --- ADD THESE IMPORTS ---
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition

def generate_launch_description():
    # 1. Path to the Aggregator configuration file
    pkg_share = get_package_share_directory('your_package_name')
    aggregator_config = os.path.join(pkg_share, 'config', 'diagnostic_aggregator.yaml')

    # --- DEFINE LAUNCH CONFIGURATION ---
    # This allows the 'use_gui' argument to be usable in conditions
    use_gui = LaunchConfiguration('use_gui')

    return LaunchDescription([
        # ------ REST OF YOUR CODE ---------

        # Declare the boolean argument for starting the RQT Robot Monitor
        DeclareLaunchArgument(
            'use_gui',
            default_value='true',   # You can change this value to 'false' if you do not want to start rqt_robot_monitor gui
            description='Start RQT Robot Monitor if true'
        ),

        # --- RQT ROBOT MONITOR ---
        # Launches the GUI to visualize the aggregated diagnostics
        Node(
            package='rqt_robot_monitor',
            executable='rqt_robot_monitor',
            name='rqt_robot_monitor',
            output='screen',
            condition=IfCondition(use_gui)
        )
    ])
```

### How the Aggregator Works

- **Pathing**: The `path` parameter determines the folder name in the GUI. For example, `path: Compute` creates a folder named **“Compute”** in the `rqt_robot_monitor` tree, allowing you to organize disparate nodes under a single logical heading.
- **`find_and_remove_prefix`**: This is used to clean up the names in the GUI. If your node reports its status as cpu_monitor: Core 0 Temp, setting the prefix to cpu_monitor will make the GUI simply show Core 0 Temp. It keeps the tree looking professional and decluttered.
- **Matching Logic**:
    - **`hardware_id`**: Groups items based on the specific ID set in the source code (e.g., matching the `Robot_Networking` ID we used in our custom Python script).
    - **`contains`**: Groups any diagnostic message that contains a specific string in its name (e.g., automatically matching any node that includes the string `"Service Health"`).
- **Severity Propagation**: This is the most critical feature of the aggregator. If a “CPU Usage” node nested deep inside the tree turns **RED (Error)**, the parent **“Compute”** folder and the top-level system status will also turn **RED**. This ensures that an operator can detect a failure at a glance without having to manually expand every single category.

## 7. The Master Launch File:

To wrap everything up, we can create a single “Master Launch File.” This script consolidates your custom network monitor, the prebuilt system monitors, the aggregator for organization, and the rqt GUI for an all-in-one health dashboard.

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # 1. Path to the Aggregator configuration file
    # This YAML defines how to group raw diagnostic messages into folders like "Compute" or "Networking"
    pkg_share = get_package_share_directory('your_package_name')
    aggregator_config = os.path.join(pkg_share, 'config', 'diagnostic_aggregator.yaml')

    return LaunchDescription([

        # --- 2. SYSTEM MONITORS (Prebuilt from diagnostics_common_diagnostics) ---

        # CPU Monitor: Tracks total processing load
        Node(
            package='diagnostics_common_diagnostics',
            executable='cpu_monitor.py',
            name='cpu_monitor',
            parameters=[{
                'warning_percentage': 85,  # Trigger WARN if CPU usage > 85%
                'window': 5                # Average over 5 readings to ignore brief spikes
            }]
        ),

        # RAM Monitor: Tracks memory and swap space
        Node(
            package='diagnostics_common_diagnostics',
            executable='ram_monitor.py',
            name='ram_monitor',
            parameters=[{
                'warning_percentage': 80,  # Trigger WARN if RAM usage > 80%
                'window': 3                # Average over 3 readings to prevent flickering
            }]
        ),

        # HD Monitor: Tracks disk space at a specific mount point
        Node(
            package='diagnostics_common_diagnostics',
            executable='hd_monitor.py',
            name='hd_monitor',
            parameters=[{
                'path': '/',               # Monitor the root directory partition
                'free_percent_low': 10.0,  # Warn if less than 10% space remains
                'free_percent_crit': 5.0   # Error if less than 5% space remains
            }]
        ),

        # --- 3. CUSTOM NETWORK MONITOR ---
        # Tracks WiFi signal strength and internet connectivity
        Node(
            package='your_package_name',
            executable='network_diagnostics.py',
            name='network_monitor',
            parameters=[{
                'ping_host': '8.8.8.8',     # DNS server to ping to verify internet access
                'interface': 'xxxx',      # CHANGE THIS: The specific WiFi hardware interface name
                'low_signal_threshold': -80 # Threshold (dBm) where WiFi is considered weak
            }]
        ),

        # --- 4. DIAGNOSTIC AGGREGATOR ---
        # Processes raw /diagnostics into a hierarchical tree on /diagnostics_agg
        Node(
            package='diagnostic_aggregator',
            executable='aggregator_node',
            name='diagnostic_aggregator',
            parameters=[aggregator_config]
        ),

        # Declare the boolean argument for starting the RQT Robot Monitor
        DeclareLaunchArgument(
            'use_gui',
            default_value='true',   # You can change this value to 'false' if you do not want to start rqt_robot_monitor gui
            description='Start RQT Robot Monitor if true'
        ),

        # --- 5. RQT ROBOT MONITOR ---
        # Launches the GUI to visualize the aggregated diagnostics
        Node(
            package='rqt_robot_monitor',
            executable='rqt_robot_monitor',
            name='rqt_robot_monitor',
            output='screen',
            condition=IfCondition(use_gui)
        )
    ])
```

Always make sure to register the launch & config folders by adding the following lines of code to your `CMakeLists.txt` file:

```
# Install Launch & Config folder
install(
  DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)
```

You can use the following command to run the launch file:

```bash
ros2 launch your_package_name aggregator.launch.py use_gui:=true
    # use_gui:=false => rqt_robot_monitor gui will NOT start. Rest nodes will start as usual.
    # use_gui:=false => rqt_robot_monitor gui will start along with rest of the listed nodes in the launch file.
    # If you omit the argument, it defaults to true and the window pops up.
```

## Appendix: ROS 2 Diagnostics Cheat Sheet

While the `rqt_robot_monitor` is the primary tool for visualization, sometimes you need to debug the raw data or tune parameters directly from the terminal. Use these commands to inspect the diagnostic pipeline.

### 1. Inspecting Topics

To verify that your nodes are actually sending data, check the two primary diagnostic topics:

- **Raw Data**: `ros2 topic echo /diagnostics` — View every raw status message coming from every node.
- **Aggregated Data**: `ros2 topic echo /diagnostics_agg` — View the organized, hierarchical data produced by the Aggregator.
- **Check Update Rate**: `ros2 topic hz /diagnostics` — Ensure that your `updater.update()` calls are happening at the expected frequency.

### 2. Tuning Thresholds on the Fly

If you find that a warning is triggering too easily (e.g., your network is slower than expected), you can change parameters without restarting the node:

- **List Parameters**: `ros2 param list /network_monitor_node`
- **Get Current Limit**: `ros2 param get /network_monitor_node low_signal_threshold`
- **Update Limit**: `ros2 param set /network_monitor_node low_signal_threshold -85`

### 3. Launching the Dashboard

If the GUI isn’t included in your launch file, you can always summon it manually:

- **Run Monitor**: `ros2 run rqt_robot_monitor rqt_robot_monitor`

---

## Chapter Summary

We have successfully transitioned from the theoretical architecture of ROS 2 Diagnostics to a fully functional implementation. By following this guide, you have moved beyond simply writing code that “works” to building a system that **communicates its own health**.

Throughout this chapter, we have:

- **Implemented C++ Boilerplates**: Integrated standardized monitoring for **Topics**, **Services**, and **Actions** using the `diagnostic_updater` library.
- **Automated System Monitoring**: Leveraged prebuilt nodes to track CPU, RAM, and Disk space without writing a single line of extra code.
- **Built Custom Diagnostics**: Created a Python-based Network Monitor to track WiFi strength and internet connectivity tailored to your specific hardware.
- **Centralized System Health**: Configured the **Diagnostic Aggregator** to transform a chaotic stream of data into a professional, hierarchical health dashboard.
- **Visualized with RQT**: Used the `rqt_robot_monitor` to give operators a clear “Green/Yellow/Red” view of the robot’s status.

With these tools in your repertoire, you are now equipped to build industrial-grade ROS 2 applications that are resilient, easy to troubleshoot, and ready for real-world deployment.

---

[← Back to Contents](00_Contents.md) | [← Previous: Chapter 20 — Understanding ROS2 Diagnostics](33_Understanding_ROS2_Diagnostics.md) | [Next: Chapter 22 — ROS2 Diagnostics Use Example →](35_ROS2_Diagnostics_Use_Example.md)
