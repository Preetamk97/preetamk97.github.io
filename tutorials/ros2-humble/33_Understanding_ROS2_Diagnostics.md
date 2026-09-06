# Chapter 33 — Understanding ROS2 Diagnostics

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 32 — Project 4 — TurtleBot3 Navigation with a Custom A\* Planner & Diagnostic System](32_Project_TurtleBot3_Navigation_with_Custom_A_Star_Planner_and_Diagnostic_System.md) | [Next Lesson: Chapter 34 — Using ROS2 Diagnostics →](34_Using_ROS2_Diagnostics.md)

---

## What is ROS 2 Diagnostics?

In a complex robotic system, “Is it working?” is a difficult question to answer. While standard logging (RCLCPP_INFO) tells us what a node is doing, it doesn’t give us a high-level overview of the robot’s health.

The ROS 2 Diagnostics framework is a standardized system for collecting, processing, and viewing health data from hardware and software components. It transforms raw sensor data and node states into a structured “Health Report” that an operator can understand at a glance.

## Why is it required in Robotics projects?

Robots are high-stakes machines. If a Lidar sensor disconnects while a robot is moving at 1 m/s, or if a motor driver overheats, the system needs to know immediately.

- **Preventative Maintenance**: Catching a “Warm” motor before it becomes a “Critical” failure.
- **Operational Awareness**: Allowing an operator to see why a robot stopped (e.g., “Network signal too low”) without digging through millions of lines of terminal logs.
- **Standardization**: It provides a uniform way for a Planner (software) and a Battery (hardware) to report their status using the same message format.

## Overall Architecture

The system works like a specialized news agency:

- **The Updaters *(Diagnostic Nodes)***: Gather data and “publish” the news.
- **The Aggregator**: Collects all raw news and organizes it into sections (e.g., “Sensors”, “Navigation”).
- **The Monitor**: A GUI that displays the organized news to the human operator.

## The Official Codebase

The core logic of ROS 2 Diagnostics is maintained in the official `ros/diagnostics` github repository.

## Packages Inside the `ros/diagnostics` Repository

These packages are the “tools” that you will use to build your health monitoring system:

| Package | Purpose |
| --- | --- |
| **`diagnostic_updater`** | Provides C++ and Python APIs for your nodes to easily publish status updates to the `/diagnostics` topic. |
| **`diagnostic_aggregator`** | The “Manager” node. It listens to raw diagnostics and uses a YAML file to group them into a tree structure for the GUI. |
| **`diagnostic_common_diagnostics`** | Contains pre-made scripts to monitor common Linux system stats like CPU usage, memory, and battery levels. |
| **`self_test`** | Contains special-purpose diagnostics APIs for hardware drivers to run “Pre-flight checks” (on-demand hardware verification) before the robot begins a mission. |
| **`diagnostic_analysis`** | Not ported to ROS2 yet |

## External Dependencies

One critical package is not in the repository above because it is considered a “Core” ROS 2 message:

- **`diagnostic_msgs`**: This package contains the actual message definitions (specifically DiagnosticStatus and DiagnosticArray). Every other diagnostic package depends on this. It defines the “language” they all speak.

## Diagnostic Severity Levels

Every diagnostic message includes a “Level” that indicates the health status of a component. These levels are standardized in diagnostic_msgs, allowing the GUI to color-code the robot’s health.

| Level | Constant | Value | Color | Description |
| --- | --- | --- | --- | --- |
| **OK** | `OK` | `0` | **Green** | The component is performing as expected. |
| **WARN** | `WARN` | `1` | **Yellow** | The component is functional but requires attention (e.g., high CPU, low battery). |
| **ERROR** | `ERROR` | `2` | **Red** | A critical failure has occurred (e.g., sensor disconnected, motor overheat). |
| **STALE** | `STALE` | `3` | **Gray** | The data is old. The aggregator hasn’t heard from this node in several seconds. |

## Necessary Installations

Because ROS 2 is modular, the availability of these packages depends on which version of ROS 2 you installed (ros-desktop vs. ros-base/core).

1. **`diagnostic_msgs`**

    This package contains the “language” of diagnostics.

    - **Status (Desktop)**: Pre-installed.
    - **Status (Base/Core)**: Usually pre-installed as a dependency for other core tools, but on very minimal systems (like a Docker “Core” image), it might be missing.
    - **Manual Install**: `sudo apt install ros-<distro>-diagnostic-msgs`
2. **The Diagnostics Stack (updater, aggregator, etc.)**

    These are the functional tools used to build the pipeline.

    - **Status (Desktop)**: The aggregator and updater packages are often omitted to keep the installation size down.
    - **Status (Base/Core)**: Definitely not installed. You must add them manually to your robot’s computer.
    - **Manual Install (The Full Stack)**: The most efficient way to get everything (Aggregator, Updater, and Common Diagnostics):

        ```bash
        sudo apt install ros-<distro>-diagnostics
        ```

3. **Visualizer: rqt_robot_monitor**

    This is the GUI tool used to actually see the health reports.

    - **Status (Desktop)**: Usually pre-installed as part of the RQT suite.
    - **Status (Base/Core)**: Not installed. Generally, you do not install this on the robot itself (to save resources), but rather on your remote laptop/workstation.
    - **Manual Install**:

        ```bash
        sudo apt install ros-<distro>-rqt-robot-monitor
        ```


## Understanding The Diagnostics Data Flow Pipeline

To understand the workflow, you must understand the Data Flow Pipeline. The system follows a “Many-to-One-to-Many” architecture centered around two primary topics.

### The First Primary Topic: `/diagnostics`

- Every node using a diagnostic updater publishes raw, unorganized messages to this topic.
- **The Message Type**: `diagnostic_msgs/msg/DiagnosticArray`.
- **The Problem**: If you run ros2 topic echo `/diagnostics` on a real robot, it is a chaotic mess of data from 50 different sources. It is impossible for a human to read, but it is the raw feed the system depends on.

### The Second Primary Topic: `/diagnostics_agg`

- While `/diagnostics` is for the machines, `/diagnostics_agg` is for the humans.
- **What it is**: This is the Aggregated Data Bus. It contains the exact same information as the raw topic `/diagnostics`, but it has been processed, and organized into a hierarchy by the ***diagnostic_aggregator***.
- **The Message Type**: Also `diagnostic_msgs/msg/DiagnosticArray`.
- **Understanding the Hierarchy between `/diagnostics` and `/diagnostics_agg`**:
    - In `/diagnostics`, a message name might simply be **power_board**.
    - In `/diagnostics_agg`, that same message is transformed into **Main Robot/Hardware/Power System/power_board**.
- **The Purpose**: This topic is what the `rqt_robot_monitor` node subscribes to. Because the data is now structured like a file system (folders and sub-folders), the GUI can display it as a clean, expandable tree rather than a flat, scrolling list of chaos.

### How the two work together (The “Many-to-One-to-Many”)

- MANY nodes (Lidar, Battery, Planner, Motor) publish Raw Messages to Topic #1: `/diagnostics`.
- ONE node (the `diagnostic_aggregator`) subscribes to that raw mess. It acts as a filter and organizer.
- That same ONE node then publishes the Sorted Results to Topic #2: `/diagnostics_agg`.
- MANY tools (like ***rqt_robot_monitor*** or a ***web dashboard***) subscribe to the sorted topic to show the robot’s health to the user.

## Core Diagnostics Package Roles & Their Functional Logic

### 1. `diagnostic_updater` (The Reporter)

This package is a **library** (not a standalone node) that you include directly into your own C++ or Python code. It provides the core software tools needed to generate, format, and send health data from within a running node.

### Key Classes and Their Roles

- **`DiagnosticStatusWrapper`**:
This is the **“Message Builder.”** Instead of manually filling out complex ROS 2 message fields, you use this class to easily set the status level (OK/WARN/ERROR) and add “Key-Value” pairs (e.g., `Temperature: 45C`). It also allows for merging multiple status reports into a single entry.
- **`Updater`**:
This is the **“Manager”** of the node’s diagnostics. It maintains a list of diagnostic tasks and handles the background timing. At every defined interval (period), it calls all registered tasks to collect their data and publishes a `DiagnosticArray` to the `/diagnostics` topic.
- **`DiagnosedPublisher`**:
A specialized version of a standard ROS 2 Publisher. Beyond sending data, it automatically monitors the **frequency** of your messages. If a node is expected to publish at 10Hz but drops to 2Hz, this class will automatically generate a “Warning” status without requiring extra logic from the developer.

### Communication Flow

- **Publishes to:** `/diagnostics`
- **Subscribes to:** Nothing (it gathers data internally from the node’s local variables and functions).

### Configurable Parameters

The behavior of the `Updater` can be tuned using these ROS 2 parameters:

- **`diagnostic_updater.period`** (default: `1.0`): Sets the publishing interval (in seconds) for the diagnostic report.
- **`diagnostic_updater.use_fqn`** (default: `false`): If set to `true`, the diagnostic name will include the Fully Qualified Name (e.g., `/ns/node_name`) instead of just the base node name.

### 2. `diagnostic_aggregator` (The Editor)

This is a **standalone node** that acts as the centralized manager of the diagnostic system. It is responsible for turning a stream of raw data into a human-readable dashboard.

### Key Components and Their Roles

- **`Aggregator` (The Node):** The main execution unit. It subscribes to the chaotic `/diagnostics` topic and buffers incoming messages. It does not decide how to sort data itself; instead, it delegates that work to **Analyzers**.
- **`Analyzer` (The Plugin Base):** The aggregator uses a plugin-based architecture (`pluginlib`). This allows developers to create custom sorting logic.

### Available Analyzer Plugins

While you can write your own, the package provides three standard analyzer types that handle almost all robotics use cases:

1. **`GenericAnalyzer`**:
The “workhorse” of the system. It groups messages based on a match (Name or Hardware ID). It supports prefix matching (e.g., grab everything starting with “Lidar”) or regex. It is defined in your YAML using `type: diagnostic_aggregator/GenericAnalyzer`.
2. **`AnalyzerGroup`**:
This is a “folder” that contains other analyzers. It allows you to create multi-level hierarchies (e.g., `Robot -> Sensors -> IMU`). It ensures that if any analyzer inside the group reports an error, the entire group reflects that status.
3. **`DiscardAnalyzer`**:
A specialized plugin used to filter out noise. If there are diagnostic messages being published that you do not want to see in your aggregated tree or GUI, this analyzer “catches” them and prevents them from being republished to `/diagnostics_agg`.

### Communication Flow

- **Subscribes to:** `/diagnostics` (Raw, flat, and high-frequency data from all nodes).
- **Publishes to:** `/diagnostics_agg` (Organized, hierarchical data processed for the GUI).

### Logic

The Aggregator processes data in “Update Rounds.” Every second, it checks its Analyzers. If a message arrives with the name `front_hokuyo_lidar`, a `GenericAnalyzer` configured with the path `Sensors/Lidar` will catch it, rename it for the display, and calculate if the entire “Sensors” category should turn Red based on that one sensor’s failure.

### 3. `diagnostic_common_diagnostics` (The System Watchers)

This package is a collection of **pre-built monitoring nodes**. Instead of writing your own code to check if your robot’s computer is melting or out of memory, you use these ready-made tools.

### Core Monitoring Tools

- **`cpu_monitor.py`**: Tracks per-core usage, load averages, and clock speeds.
- **`hd_monitor.py`**: Checks disk space usage on specific partitions.
- **`ntp_monitor.py`**: Ensures the robot’s clock is synchronized with a network time protocol (NTP) server (critical for multi-robot systems).
- **`ram_monitor.py`**: Monitors total, used, and free physical memory (RAM). It is vital for detecting if a node has a memory leak before the OOM (Out Of Memory) killer terminates your ROS 2 processes.
- **`sensors_monitor`**: It uses the `LM_Sensors` package to get real-time data like hardware temperature, voltage and fan speed.

### Communication Flow

- **Publishes to:** `/diagnostics`
- **Subscribes to:** Nothing (they query the Linux `/proc` and `/sys` filesystems directly).

### Logic

These nodes function as standard ROS 2 nodes using the `diagnostic_updater` library. They are configured with **thresholds**. For example, the `ram_monitor` might be set to `WARN` at 85% RAM usage and `ERROR` at 95%.

### 4. `self_test` (The Doctor)

Unlike the “Reporter” (`diagnostic_updater`) which runs quietly in the background while the robot moves, `self_test` is a **C++ API** used for intensive, “stop-everything” hardware checkups. Think of it as a pre-flight checklist for a pilot: you don’t check the engine oil levels while the plane is mid-air; you do it on the ground before take-off.

### Key Classes and Their Roles

- **`SelfTest` Class**:
A wrapper that adds a **Service** (not just a topic) to your node. When this service is called, it tells the node: *“Stop your normal routine; we are starting a health exam.”*
- **`TestRunner`**:
The internal engine that follows the checklist. It executes a sequence of “Diagnostic Tasks” one by one and collects the results into a single report.

### Communication Flow

- **Service Interface:** `/<node_name>/self_test` (Type: `diagnostic_msgs/srv/SelfTest`).
- **Trigger:** This does **not** run automatically. A human or a startup script must manually call the service to start the test.
- **Output:** Once the test finishes, the results are sent to the `/diagnostics` topic as a final summary.

### How it works (The Logic)

When you trigger a `self_test`, the node enters a dedicated “Testing Mode.” It executes tasks in a specific order that might be unsafe to do during normal operation.

**Example: Motor Driver Pre-Flight Check**

1. **Voltage Check:** “Is the battery providing enough power to move?”
2. **Bridge Test:** “Can I safely send current to the motor coils?”
3. **Movement Test:** “Move the wheel 5 degrees and verify the encoder sees the movement.”
4. **Result:** The node returns a “Passed” or “Failed” status and then resumes its normal ROS 2 behavior.

## Understanding the Message Structures

The three main message interfaces used in the ROS 2 diagnostics pipeline are `diagnostic_msgs/msg/DiagnosticArray`, `diagnostic_msgs/msg/DiagnosticStatus`, and `diagnostic_msgs/msg/KeyValue`.

To understand how these work together, think of the **DiagnosticArray** as a folder containing several “reports” (**DiagnosticStatus**). Each of those reports can have multiple specific data points (**KeyValue**) attached to them to explain the findings.

---

### 1. Structure of `diagnostic_msgs/msg/DiagnosticArray`

This is the top-level container. It is the only message-type that gets actually published to the `/diagnostics` topic. Its job is to bundle multiple component statuses together so they are sent with a single timestamp.

| Field | Type | Meaning |
| --- | --- | --- |
| **header** | `std_msgs/Header` | Contains the timestamp (`stamp`). This tells the system exactly when these diagnostics were captured. |
| **status** | `DiagnosticStatus[]` | A Vector (list) of status messages. This allows one node to report on many things at once (e.g., both “Network Health” and “CPU Load”). |

### Deep Dive: The `std_msgs/Header` Interface

Since the Header is a component of the `DiagnosticArray`, it acts as the “official time-stamp” for the entire report folder.

| Field | Type | Meaning |
| --- | --- | --- |
| **stamp** | `builtin_interfaces/Time` | The exact moment the message was generated (seconds and nanoseconds). |
| **frame_id** | `string` | In diagnostics, this is usually empty. We rely on the `hardware_id` inside the status to identify the source. |

---

### 2. Structure of `diagnostic_msgs/msg/DiagnosticStatus`

This interface represents the health of a single component or test. It is the “meat” of the diagnostic system where the actual logic results are stored.

| Field | Type | Meaning |
| --- | --- | --- |
| **level** | `byte` | The health state: 0 (OK), 1 (WARN), 2 (ERROR), 3 (STALE). |
| **name** | `string` | The human-readable name of the test (e.g., “A\* Planner Path Check”). |
| **message** | `string` | A brief description of the status (e.g., “Path found in 0.05s”). |
| **hardware_id** | `string` | A unique ID for the hardware/software (e.g., “turtlebot3_network_card”). |
| **values** | `KeyValue[]` | A Vector of extra data points providing detailed context. |

---

### 3. Structure of `diagnostic_msgs/msg/KeyValue`

The `KeyValue` interface is the smallest unit. It allows you to attach raw data to a status report without defining a new message type. It follows a simple **“Label: Value”** format.

| Field | Type | Meaning |
| --- | --- | --- |
| **key** | `string` | The label for the data point (e.g., “Signal Strength”). |
| **value** | `string` | The actual data. **Note:** All values must be converted to strings (e.g., “75%”) even if they were originally numbers. |

---

### Summary of Data Flow

In a typical diagnostic node (like our network monitor), the data flows “upward” through these structures:

1. **Value** (e.g., `60 dBm`) → Converted to **String** → Stored in **`KeyValue`**.
2. **`KeyValue`** → Pushed into the `values` list of a **`DiagnosticStatus`**.
3. **`DiagnosticStatus`** → Pushed into the `status` list of the **`DiagnosticArray`**.
4. **`DiagnosticArray`** → Published to the **`/diagnostics`** topic!

---

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 32 — Project 4 — TurtleBot3 Navigation with a Custom A\* Planner & Diagnostic System](32_Project_TurtleBot3_Navigation_with_Custom_A_Star_Planner_and_Diagnostic_System.md) | [Next Lesson: Chapter 34 — Using ROS2 Diagnostics →](34_Using_ROS2_Diagnostics.md)

