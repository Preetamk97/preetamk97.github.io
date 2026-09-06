# Chapter 32 — Project 4 — TurtleBot3 Navigation with a Custom A\* Planner & Diagnostic System

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 31 — ROS2 Actions (C++)](31_ROS2_Actions_Cpp.md) | [Next Lesson: Chapter 33 — Understanding ROS2 Diagnostics →](33_Understanding_ROS2_Diagnostics.md)

---

## 0. Prerequisites and Installations

Before setting up the project, ensure the following tools and packages are installed on your ROS 2 system (Humble/Foxy/Galactic).

System Requirements:

- Ubuntu 20.04 or 22.04 (depending on ROS version)
- ROS 2 Desktop Full Installation

**Required Packages**: Install the necessary Gazebo simulators and Navigation2 stacks:

```bash
sudo apt install ros-$ROS_DISTRO-gazebo-*
sudo apt install ros-$ROS_DISTRO-cartographer
sudo apt install ros-$ROS_DISTRO-cartographer-ros
sudo apt install ros-$ROS_DISTRO-navigation2
sudo apt install ros-$ROS_DISTRO-nav2-bringup
sudo apt install ros-$ROS_DISTRO-diagnostic-updater
sudo apt install ros-$ROS_DISTRO-diagnostic-aggregator
sudo apt install ros-$ROS_DISTRO-rqt-robot-monitor
sudo apt install python3-colcon-common-extensions
```

### 1. Setting up the Project

#### 1.1 Create the Workspace

- Inside the **turtlebot3_ws** workspace folder create a src directory.

    ```bash
    mkdir -p ~/turtlebot3_ws/src
    ```

#### 1.2 Clone Repositories

We need the official TurtleBot3 source codes to run the simulation. Clone the following repositories into the src folder:

```bash
git clone -b $ROS_DISTRO https://github.com/ROBOTIS-GIT/turtlebot3.git
git clone -b $ROS_DISTRO https://github.com/ROBOTIS-GIT/turtlebot3_msgs.git
git clone -b $ROS_DISTRO https://github.com/ROBOTIS-GIT/turtlebot3_simulations.git
git clone -b $ROS_DISTRO https://github.com/ROBOTIS-GIT/DynamixelSDK.git
```

#### 1.3 Build the Workspace

Navigate back to the root of the workspace and build the packages using colcon.

```bash
cd ~/turtlebot3_ws
rosdep update
rosdep install --from-paths src -y --ignore-src
colcon build --symlink-install
source install/setup.bash
```

### 2. Running Basic Simulation and Navigation

#### 2.1 Launching Gazebo

Set the robot model environment variable (e.g., burger, waffle, or waffle_pi) and launch the simulation world.

**Terminal 1:**

```bash
cd ~/turtlebot3_ws/
source install/setup.bash
export TURTLEBOT3_MODEL=waffle
source /usr/share/gazebo/setup.bash
source /usr/share/gazebo/setup.sh
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
```

#### 2.2 Mapping (SLAM)

To create a map of the environment, launch the SLAM node while Gazebo is running.

***Note:** Keep the Gazebo Window Opened.*

**Terminal 2:**

```bash
cd ~/turtlebot3_ws/
source install/setup.bash
export TURTLEBOT3_MODEL=waffle
ros2 launch turtlebot3_cartographer cartographer.launch.py use_sim_time:=True
```

- Open a new terminal on the Remote PC with Ctrl + Alt + T and run the teleoperation node from the Remote PC. Specify your TurtleBot3 model (waffle) using the TURTLEBOT3_MODEL parameter.

    **Terminal 3:**

    ```bash
    cd ~/turtlebot3_ws/
    source install/setup.bash
    export TURTLEBOT3_MODEL=waffle
    ros2 run turtlebot3_teleop teleop_keyboard
    ```


#### 2.3 Saving the Map

Once satisfied with the map, save it to your disk.

```bash
ros2 run nav2_map_server map_saver_cli -f ~/map
```

#### 2.4 Starting Navigation (Nav2)

Close the SLAM node and launch the Navigation2 stack using your saved map.

```bash
cd ~/turtlebot3_ws/
source install/setup.bash
export TURTLEBOT3_MODEL=waffle
ros2 launch turtlebot3_navigation2 navigation2.launch.py map:=$HOME/map.yaml
```

### 3. Custom Global Planner Plugin (A\*)

This section details the creation of a custom Global Planner plugin compliant with the nav2_core interface.

#### 3.1 Creating the Package

Create a new package with rclcpp and nav2_core dependencies.

```bash
cd ~/turtlebot3_ws/src
ros2 pkg create --build-type ament_cmake custom_a_star_planner --dependencies rclcpp nav2_core nav2_util pluginlib nav2_costmap_2d geometry_msgs
```

#### 3.2 Implementation

The core logic was implemented in C++. This plugin inherits from nav2_core::GlobalPlanner and implements the createPlan method using the A\* algorithm.

**File: `src/a_star_planner.cpp`**

```cpp
#include<cmath>
#include<queue>
#include<vector>
#include<unordered_map>
#include<algorithm>

#include"pluginlib/class_list_macros.hpp"
#include"custom_a_star_planner/a_star_planner.hpp"

namespace custom_a_star_planner
{

void AStarPlanner::configure(
  const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
  std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros)
{
  costmap_ros_ = costmap_ros;
  costmap_ = costmap_ros_->getCostmap();
  name_ = name;
}

void AStarPlanner::cleanup() {}
void AStarPlanner::activate() {}
void AStarPlanner::deactivate() {}

nav_msgs::msg::Path AStarPlanner::createPlan(
  const geometry_msgs::msg::PoseStamped & start,
  const geometry_msgs::msg::PoseStamped & goal)
{
  // Artificial delay to trigger Diagnostic WARN (e.g., 600ms)
  // std::this_thread::sleep_for(std::chrono::milliseconds(600));

  // --- GOAL GATE: Prevent replanning if a path already exists & the goal hasn't changed ---
  if (!latest_path_.poses.empty() &&
      std::abs(latest_goal_.pose.position.x - goal.pose.position.x) < 0.01 &&
      std::abs(latest_goal_.pose.position.y - goal.pose.position.y) < 0.01)
  {
    // Return saved path but update the timestamp so Nav2 doesn't think it's stale
    // In ROS 2, almost every message has a header.stamp. This timestamp tells other nodes
    // exactly when this data was created.
    // The start pose passed into createPlan comes from the Localizer (AMCL). Even if the robot is
    // standing perfectly still, AMCL is constantly publishing the robot's position at a high frequency
    // (e.g., 20Hz). Each time it publishes, the start.header.stamp is updated to the current
    // simulation time.
    // If your "Goal Gate" triggers, you are grabbing a latest_path_ that might have been calculated 5 seconds ago. If you return that path with the old timestamp, the Controller Server (the "Driver")
    // might see it and say: "This path is 5 seconds old. That's ancient history in robot time! I'm
    // going to ignore it for safety."
    // By setting latest_path_.header.stamp = start.header.stamp, you are essentially "freshening up"
    // the old path. You are telling the rest of the Nav2 stack: "This path is still valid for right now."
    latest_path_.header.stamp = start.header.stamp;
    return latest_path_;
  }

  nav_msgs::msg::Path global_path;
  global_path.header.stamp = start.header.stamp;
  global_path.header.frame_id = "map";

  // 1. Convert World Coordinates to Map Coordinates
  // 2. worldToMap : It translates the coordinates from the continuous physical world into the discrete
  //  world of pixels (cells) that the computer uses to perform the A* search.
  // start.pose.position.x: The robot's location in meters.
  // start_x: The resulting grid column index (unsigned integer).
  // 3. The costmap_->worldToMap(...) function also returns a Boolean (true or false).
  // -  true: The coordinate is inside the boundaries of the map.
  // -  false: The coordinate is "off the map."
  unsigned int start_x, start_y, goal_x, goal_y;
  if (!costmap_->worldToMap(start.pose.position.x, start.pose.position.y, start_x, start_y) ||
      !costmap_->worldToMap(goal.pose.position.x, goal.pose.position.y, goal_x, goal_y))
  {
    return global_path;
  }

  // This line converts 2D grid coordinates (row and column) into 1D index numbers for each cell.
  unsigned int start_idx = costmap_->getIndex(start_x, start_y);
  unsigned int goal_idx = costmap_->getIndex(goal_x, goal_y);

  // 2. Initialize A* Data Structures
  std::priority_queue<Node, std::vector<Node>, std::greater<Node>> open_list;
  std::unordered_map<unsigned int, double> g_costs;
  std::unordered_map<unsigned int, unsigned int> parent_map;

  open_list.push({start_idx, 0.0, euclidean_distance(start_idx, goal_idx), 0.0, start_idx});
  g_costs[start_idx] = 0.0;

  bool goal_found = false;

  // 3. Main A* Loop
  while (!open_list.empty()) {
    Node current = open_list.top();
    open_list.pop();

    if (current.index == goal_idx) {
      goal_found = true;
      break;
    }

    for (unsigned int neighbor_idx : get_neighbors(current.index)) {
      if (costmap_->getCost(neighbor_idx) >= 253) continue;

      double move_cost = euclidean_distance(current.index, neighbor_idx);
      double new_g = current.g + move_cost;

      if (g_costs.find(neighbor_idx) == g_costs.end() || new_g < g_costs[neighbor_idx]) {
        g_costs[neighbor_idx] = new_g;
        double h = euclidean_distance(neighbor_idx, goal_idx);
        double f = new_g + h;

        parent_map[neighbor_idx] = current.index;
        open_list.push({neighbor_idx, new_g, h, f, current.index});
      }
    }
  }

  // 4. Path Reconstruction
  if (goal_found) {
    unsigned int curr = goal_idx;
    while (curr != start_idx) {
      geometry_msgs::msg::PoseStamped pose;
      double world_x, world_y;
      unsigned int mx, my;
      costmap_->indexToCells(curr, mx, my);
      costmap_->mapToWorld(mx, my, world_x, world_y);

      pose.header = global_path.header;
      pose.pose.position.x = world_x;
      pose.pose.position.y = world_y;
      pose.pose.orientation.w = 1.0;
      global_path.poses.push_back(pose);

      curr = parent_map[curr];
    }
    global_path.poses.push_back(start);
    std::reverse(global_path.poses.begin(), global_path.poses.end());

    // Fix final orientation
    if (!global_path.poses.empty()) {
        global_path.poses.back().pose.orientation = goal.pose.orientation;
    }

    // Save for the Goal Gate
    latest_path_ = global_path;
    latest_goal_ = goal;
  }

  return global_path;
}

double AStarPlanner::euclidean_distance(unsigned int start_index, unsigned int goal_index) {
  unsigned int x1, y1, x2, y2;
  costmap_->indexToCells(start_index, x1, y1);
  costmap_->indexToCells(goal_index, x2, y2);
  return std::hypot(static_cast<double>(x1) - x2, static_cast<double>(y1) - y2);
}

std::vector<unsigned int> AStarPlanner::get_neighbors(unsigned int index) {
  std::vector<unsigned int> neighbors;
  unsigned int mx, my;
  costmap_->indexToCells(index, mx, my);

  for (int dx = -1; dx <= 1; ++dx) {
    for (int dy = -1; dy <= 1; ++dy) {
      if (dx == 0 && dy == 0) continue;
      unsigned int nx = mx + dx;
      unsigned int ny = my + dy;
      if (nx < costmap_->getSizeInCellsX() && ny < costmap_->getSizeInCellsY()) {
        neighbors.push_back(costmap_->getIndex(nx, ny));
      }
    }
  }
  return neighbors;
}

} // namespace custom_a_star_planner

#include"pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(custom_a_star_planner::AStarPlanner, nav2_core::GlobalPlanner)
```

**File: `include/custom_a_star_planner/a_star_planner.hpp`**

```cpp
#ifndef CUSTOM_A_STAR_PLANNER__A_STAR_PLANNER_HPP_
#define CUSTOM_A_STAR_PLANNER__A_STAR_PLANNER_HPP_

#include<memory>
#include<string>
#include<vector>
#include<queue>
#include<unordered_map>

#include"geometry_msgs/msg/point.hpp"
#include"geometry_msgs/msg/pose_stamped.hpp"
#include"nav2_core/global_planner.hpp"
#include"nav_msgs/msg/path.hpp"
#include"nav2_util/robot_utils.hpp"
#include"nav2_util/lifecycle_node.hpp"
#include"nav2_costmap_2d/costmap_2d_ros.hpp"

namespace custom_a_star_planner
{

struct Node {
  unsigned int index;
  double g;
  double h;
  double f;
  unsigned int parent_index;

  bool operator>(const Node& other) const {
    return f > other.f;
  }
};

class AStarPlanner : public nav2_core::GlobalPlanner
{
public:
  AStarPlanner() = default;
  ~AStarPlanner() = default;

  void configure(const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;

  void cleanup() override;
  void activate() override;
  void deactivate() override;

  nav_msgs::msg::Path createPlan(
    const geometry_msgs::msg::PoseStamped & start,
    const geometry_msgs::msg::PoseStamped & goal) override;

private:
  double euclidean_distance(unsigned int start_index, unsigned int goal_index);
  std::vector<unsigned int> get_neighbors(unsigned int index);

  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros_;
  nav2_costmap_2d::Costmap2D * costmap_;
  std::string name_;

  // Logic to prevent continuous replanning
  nav_msgs::msg::Path latest_path_;
  geometry_msgs::msg::PoseStamped latest_goal_;
};

}  // namespace custom_a_star_planner

#endif
```

#### 3.3 Plugin Registration

To make the planner visible to the ROS 2 plugin system, we registered it using pluginlib.

**File: `export_plugins.xml` (Created in package root)**

```xml
<library path="libcustom_a_star_planner">
  <class name="custom_a_star_planner/AStarPlanner"
         type="custom_a_star_planner::AStarPlanner"
         base_class_type="nav2_core::GlobalPlanner">
    <description>Custom A* Planner</description>
  </class>
</library>
```

#### 3.4 Build Configuration

Updated CMakeLists.txt to compile the library and export the plugin.

**File: `CMakeLists.txt`**

```c
cmake_minimum_required(VERSION 3.8)
project(custom_a_star_planner)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

#Find dependencies
find_package(ament_cmake REQUIRED)
find_package(nav2_core REQUIRED)
find_package(rclcpp REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(pluginlib REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(nav2_util REQUIRED)
find_package(diagnostic_updater REQUIRED)
find_package(action_msgs REQUIRED)

# 2. Add the Diagnostic Node Executable
add_executable(planner_diagnostics_node src/planner_diagnostics_node.cpp)
ament_target_dependencies(planner_diagnostics_node
  rclcpp
  nav_msgs
  geometry_msgs
  action_msgs
  diagnostic_updater
)

install(TARGETS
  planner_diagnostics_node
  DESTINATION lib/${PROJECT_NAME}
)

#Create the shared library
add_library(custom_a_star_planner SHARED
  src/a_star_planner.cpp
)

# Include directories
target_include_directories(custom_a_star_planner PUBLIC
  "$<BUILD_INTERFACE:
${CMAKE_CURRENT_SOURCE_DIR}/include>"
  $<INSTALL_INTERFACE:include>
)

#Target dependencies
ament_target_dependencies(custom_a_star_planner
  nav2_core
  rclcpp
  nav_msgs
  geometry_msgs
  pluginlib
  nav2_costmap_2d
  nav2_util
)

#Install the library
install(TARGETS custom_a_star_planner
  EXPORT export_custom_a_star_planner
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

#Install the config directory so the YAML file is found
install(DIRECTORY config
  DESTINATION share/${PROJECT_NAME}
)

#Install the plugin description file
install(FILES export_plugins.xml
  DESTINATION share/${PROJECT_NAME}
)

#Install headers
install(DIRECTORY include/
  DESTINATION include/
)

ament_export_targets(export_custom_a_star_planner HAS_LIBRARY_TARGET)

#This registers the plugin with the ament index so nav2_core can find it
ament_export_libraries(custom_a_star_planner)
pluginlib_export_plugin_description_file(nav2_core export_plugins.xml)

ament_package()
```

**File: `package.xml`**

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>custom_a_star_planner</name>
  <version>0.0.0</version>
  <description>TODO: Package description</description>
  <maintainer email="pritam@todo.todo">pritam</maintainer>
  <license>TODO: License declaration</license>

  <buildtool_depend>ament_cmake</buildtool_depend>

  <depend>nav2_core</depend>
  <depend>rclcpp</depend>
  <depend>nav_msgs</depend>
  <depend>geometry_msgs</depend>
  <depend>pluginlib</depend>
  <depend>nav2_costmap_2d</depend>
  <depend>action_msgs</depend>
  <depend>diagnostic_updater</depend>

  <test_depend>ament_lint_auto</test_depend>
  <test_depend>ament_lint_common</test_depend>

  <export>
  <build_type>ament_cmake</build_type>
  <nav2_core plugin="${prefix}/export_plugins.xml" />
  </export>

</package>
```

#### 3.5 Integration with Nav2: Changing the Default Global Planner to Custom A\* Planner

- In order to change the planner-plugin that is used by the Navigation2 stack’s `planner_server` node, firstly a new folder named `config` is created inside the **custom_a_star_planner** package and inside it the file named **waffle.yaml** which is copied directly from ***turtlebot3_ws/src/turtlebot3/turtlebot3_navigation2/param*** directory is pasted and renamed as ***custom_nav_params.yaml***.

    This is the default *.yaml* configuration file that the `turtlebot3/turtlebot3_navigation` package uses upon running the bash command for default navigation:

    ```
    ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$HOME/map.yaml
    ```

- In the file ***custom_nav_params*** the field ***planner_server:GridBased:plugin*** is changed from its default value to `"custom_a_star_planner/AStarPlanner"`.

    ```yaml
    planner_server:
      ros__parameters:
        expected_planner_frequency: 0.0
        planner_plugins: ["GridBased"]
        GridBased:
          plugin: "custom_a_star_planner/AStarPlanner"   # custom A* class
    ```


In order to use this particular params file while launching your navigation node use the following command:

```bash
ros2 launch turtlebot3_navigation2 navigation2.launch.py \
  use_sim_time:=True \
  map:=$HOME/map.yaml \
  params_file:=$(ros2 pkg prefix custom_a_star_planner)/share/custom_a_star_planner/config/custom_nav_params.yaml
```

### 4. Diagnostic & Monitoring System

To ensure robustness, we developed a 3-layer diagnostic system:

- Controller Diagnostics
- Planner Diagnostics
- Network Monitor

#### 4.1 Controller Diagnostics Node (C++)

Monitors the controller_server health via heartbeat checks on /cmd_vel and detects if the robot is stalled (moving but position not changing).

**File: `src/controller_diagnostics_node.cpp`**

```cpp
#include<chrono>
#include<memory>
#include<cmath>

#include"rclcpp/rclcpp.hpp"
#include"geometry_msgs/msg/twist.hpp"
#include"action_msgs/msg/goal_status_array.hpp"
#include"diagnostic_updater/diagnostic_updater.hpp"

using namespace std::chrono_literals;

class ControllerDiagnosticsNode : public rclcpp::Node
{
public:
  ControllerDiagnosticsNode()
  : Node("controller_diagnostics_node"),
    goal_active_(false),
    robot_stuck(false),
    status(0) // 0 = No goal yet
  {
    cmd_vel_sub_ = this->create_subscription<geometry_msgs::msg::Twist>(
      "/cmd_vel", 10, std::bind(&ControllerDiagnosticsNode::cmd_vel_callback, this, std::placeholders::_1));

    status_sub_ = this->create_subscription<action_msgs::msg::GoalStatusArray>(
      "/navigate_to_pose/_action/status", 10,
      std::bind(&ControllerDiagnosticsNode::status_callback, this, std::placeholders::_1));

    updater_.setHardwareID("TurtleBot3_Controller_System");
    updater_.add("Controller Server Health", this, &ControllerDiagnosticsNode::produce_diagnostics);

    auto now = this->now();
    last_cmd_time_ = now;
    last_movement_time_ = now;

    RCLCPP_INFO(this->get_logger(), "Controller Diagnostics Node Started.");

  }

private:

  void status_callback(const action_msgs::msg::GoalStatusArray::SharedPtr msg)
  {
    if (msg->status_list.empty()) return;

    status = msg->status_list.back().status;

    // Status 1 (Accepted) or 2 (Executing)
    if (status == 1 || status == 2) {
      if (!goal_active_) {
        goal_active_ = true;
        robot_stuck = false;

        // Reset timers on new goal start
        auto now = this->now();
        last_movement_time_ = now;
        last_cmd_time_ = now;
      }
    }
    // Status >= 4 (Succeeded, Aborted, Canceled)
    else if (status >= 3) {
      goal_active_ = false;
    }
  }

  void cmd_vel_callback(const geometry_msgs::msg::Twist::SharedPtr msg)
  {
    auto now = this->now();
    last_cmd_time_ = now;

    // Check if robot is effectively stationary
    if (std::abs(msg->linear.x) < 0.1 && std::abs(msg->angular.z) < 0.1) {
      robot_stuck = true;
    } else {
      robot_stuck = false;
      last_movement_time_ = now;   // Last time when the robot decided to move.
    }
  }

  void produce_diagnostics(diagnostic_updater::DiagnosticStatusWrapper & stat)
  {
    auto now = this->now();
    double gap = (now - last_cmd_time_).seconds();
    double move_time = (now - last_movement_time_).seconds();

    // 1. HEARTBEAT CHECK: cmd_vel messages are not coming
    if (gap > 3.0) {
      if (status == 5) { // 5 = ABORTED
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Mission Abort!");
      }
      else if (status == 6) { // 6 = CANCELLED
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Controller stopped (Goal Cancelled).");
      }
      else if (status == 4) {  // 4 = SUCCEEDED
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Idle / Goal Succeeded");
      }
      else if (status==3) {
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Cancelling the Goal");
      }
      else if (status == 0) {
        // Startup/init state
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Idle: System Ready.");
      }
      else {
        // Heartbeat lost during execution (Status 1 or 2)
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::ERROR, "Controller Node Heartbeat Lost");
      }
    }
    // 2. Check if the goal is active
    // Is the below block necessary ? : Yes, it is practically necessary. Imagine the robot
    // finishes a goal. The controller stops sending /cmd_vel immediately. For the next 2.99
    // seconds, your code will skip the first if block. Without the else if: The code would fall into the final else (the "Active" logic).
    else if (!goal_active_) {
      stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Goal Not Active Currently !");
    }

    // 3. cmd_vel messages are coming.
    else {
      if (robot_stuck || move_time > 0.1) {
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Robot Stalled");
      }
      else if (gap > 0.5) {
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "Controller Lagging (Low Frequency).");
      }
      else {
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Controller working fine.");
      }
    }

    stat.add("Goal Active", goal_active_ ? "Yes" : "No");
    // stat.add("Last Status Code", std::to_string(status));
    stat.add("Last Status Code", status);
    stat.add("Time since last movement (s)", move_time);
    stat.add("Cmd_vel Gap (s)", gap);
  }

  diagnostic_updater::Updater updater_{this};
  rclcpp::Subscription<geometry_msgs::msg::Twist>::SharedPtr cmd_vel_sub_;
  rclcpp::Subscription<action_msgs::msg::GoalStatusArray>::SharedPtr status_sub_;

  rclcpp::Time last_cmd_time_;
  rclcpp::Time last_movement_time_;

  bool goal_active_;
  bool robot_stuck;
  int8_t status;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<ControllerDiagnosticsNode>();
  rclcpp::spin(node);
  rclcpp::shutdown();
  return 0;
}
```

#### 4.2 Planner Diagnostics Node (C++)

Monitors the planner_server to ensure path calculation requests are being processed.

**File: `src/planner_diagnostics_node.cpp`**

```cpp
#include<chrono>
#include<memory>
#include<vector>

#include"rclcpp/rclcpp.hpp"
#include"nav_msgs/msg/path.hpp"
#include"action_msgs/msg/goal_status_array.hpp"
#include"diagnostic_updater/diagnostic_updater.hpp"

using namespace std::chrono_literals;

class AStarDiagnosticsNode : public rclcpp::Node
{
public:
  AStarDiagnosticsNode()
  : Node("astar_diagnostics_node"),
    goal_active_(false),
    path_received_(false),
    initial_wait_ms_(0.0)
  {
    // Plan: Monitor the output of the A* Planner plugin
    plan_sub_ = this->create_subscription<nav_msgs::msg::Path>(
      "/plan", 10, std::bind(&AStarDiagnosticsNode::path_callback, this, std::placeholders::_1));

    // Status: Monitor /navigate_to_pose action to track mission lifecycle
    status_sub_ = this->create_subscription<action_msgs::msg::GoalStatusArray>(
      "/navigate_to_pose/_action/status", 10,
      std::bind(&AStarDiagnosticsNode::status_callback, this, std::placeholders::_1));

    updater_.setHardwareID("TurtleBot3_AStar_System");
    updater_.add("Custom A* Planner Health", this, &AStarDiagnosticsNode::produce_diagnostics);

    RCLCPP_INFO(this->get_logger(), "A* Diagnostics Node Initialized.");
  }

private:
  void path_callback(const nav_msgs::msg::Path::SharedPtr msg)
  {
    current_path_ = msg;

    if (!path_received_) {
      path_received_ = true;
      double seconds = (this->now() - start_time_).seconds();
      initial_wait_ms_ = seconds * 1000.0;
    }
  }

  void status_callback(const action_msgs::msg::GoalStatusArray::SharedPtr msg)
  {
    if (msg->status_list.empty()) return;
    int8_t status = msg->status_list.back().status;

    if (status == 1 || status == 2) {
      if (!goal_active_) {
        goal_active_ = true;
        path_received_ = false;
        initial_wait_ms_ = 0.0;
        start_time_ = this->now();
      }
    }
    else if (status >= 3) {
      if (goal_active_) {
        goal_active_ = false;
        path_received_ = false;
      }
    }
  }

  void produce_diagnostics(diagnostic_updater::DiagnosticStatusWrapper & stat)
  {
    if (!goal_active_) {
      stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Idle: Waiting for goal");
      return;
    }

    if (!path_received_) {
      double live_wait_ms = (this->now() - start_time_).seconds() * 1000.0;
      if (live_wait_ms > 3000.0) {
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::ERROR, "Something is Wrong. Path Plan Did Not Arrive !");
      } else {
        stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "Planning in progress...");
      }
      stat.add("Total User Wait (ms)", live_wait_ms);
      return;
    }

    // Once Path is Recieved
    // Report based on the locked initial latency
    if (initial_wait_ms_ > 500.0) {
      stat.summary(diagnostic_msgs::msg::DiagnosticStatus::WARN, "High Initial Latency");
    } else {
      stat.summary(diagnostic_msgs::msg::DiagnosticStatus::OK, "A* Planner Healthy");
    }

    stat.add("Total User Wait (ms)", initial_wait_ms_);

    // Safety check for waypoint display
    if (current_path_) {
      stat.add("Current Path Waypoints", current_path_->poses.size());
    }
  }

  diagnostic_updater::Updater updater_{this};
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr plan_sub_;
  rclcpp::Subscription<action_msgs::msg::GoalStatusArray>::SharedPtr status_sub_;
  nav_msgs::msg::Path::SharedPtr current_path_;
  rclcpp::Time start_time_;
  bool goal_active_;
  bool path_received_;
  double initial_wait_ms_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<AStarDiagnosticsNode>());
  rclcpp::shutdown();
  return 0;
}
```

#### 4.3 Network Monitor Node (Python)

A custom script that monitors WiFi signal strength (RSSI) from /proc/net/wireless and verifies internet connectivity via DNS socket connection.

**File: `scripts/network_diagnostics.py.py`**

```bash
#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from diagnostic_updater import Updater, DiagnosticStatusWrapper
import socket
import os

class NetworkMonitor(Node):
    def __init__(self):
        # Name the node "network_diagnostics.py"
        super().__init__('network_diagnostics.py')

        # 1. Declare Parameters
        self.declare_parameter('ping_host', '8.8.8.8')
        self.declare_parameter('interface', 'wlp8s0')
        self.declare_parameter('low_signal_threshold', -75)

        # 2. Setup Parameter Callback (Triggers when you use 'ros2 param set')
        self.add_on_set_parameters_callback(self.parameter_callback)

        # 3. Setup Diagnostics
        self.updater = Updater(self)
        self.updater.setHardwareID("Robot_Networking")
        self.updater.add("Wifi and Internet Status", self.check_network)

        self.get_logger().info("Network Monitor Node Started. Checking interface: %s" %
                               self.get_parameter('interface').value)

    def parameter_callback(self, params):
        """Logs changes made to parameters via CLI or other nodes."""
        for param in params:
            self.get_logger().info(f"Parameter '{param.name}' changed to: {param.value}")
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
            self.get_logger().debug(f"Could not read wireless stats: {e}")
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
            stat.summary(stat.WARN, f"Weak WiFi Signal: {level} dBm")
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

- **Note**: Ensure this file is executable: `chmod +x scripts/network_diagnostics.py`
inside the directory where this file is currently located.

#### 4.4 Diagnostic Aggregator

To organize the raw data in the RQT dashboard, we configured a Diagnostic Aggregator using a YAML file.

**File: `nav_aggregator.yaml`**

```yaml
# nav_aggregator.yaml
diagnostic_aggregator:
  ros__parameters:
    analyzers:
      # Analyzer for the Controller Node
      controller_analyzer:
        type: diagnostic_aggregator/GenericAnalyzer
        path: 'Controller'                  # Appears as "Controller" in the tree
        find: 'Controller Server Health'
        timeout: 5.0                        # If no update for 5 seconds, mark as STALE

      # Analyzer for the Planner Node
      planner_analyzer:
        type: diagnostic_aggregator/GenericAnalyzer
        path: 'Planner'                     # Appears as "Planner" in the tree
        find: 'Custom A* Planner Health'
        timeout: 5.0                        # If no update for 5 seconds, mark as STALE

      # Inside your nav_aggregator.yaml analyzers:
      network:
        type: diagnostic_aggregator/GenericAnalyzer
        path: 'Network'
        find: 'Wifi and Internet Status'
        timeout: 5.0                        # If no update for 5 seconds, mark as STALE
```

#### 4.5 System Launch File

A unified launch file was created to start all diagnostic nodes and the aggregator simultaneously, along with the RQT Robot Monitor.

**File: `launch/aggregator.launch.py`**

```python
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import LogInfo

def generate_launch_description():
    # Define the path to your yaml file
    config_path = os.path.join(
        get_package_share_directory('turtlebot3_navigation2'),
        'config',
        'nav_aggregator.yaml'
    )

    return LaunchDescription([
        # 1. Controller Diagnostics Node
        Node(
            package='turtlebot3_navigation2',
            executable='controller_diagnostics_node',
            name='controller_diagnostics_node',
            output='screen'
        ),

        # 2. Planner Diagnostics Node
        Node(
            package='custom_a_star_planner',
            executable='planner_diagnostics_node',
            name='planner_diagnostics_node',
            output='screen'
        ),

        # 3. Network Diagnostics
        Node(
        package='turtlebot3_navigation2',
        executable='network_diagnostics.py', # Use the full filename here
        name='network_diagnostics_node',
        parameters=[{
            'interface': 'wlp8s0',           # Your interface name
            'low_signal_threshold': -75,    # When to show a WARN
            'ping_host': '8.8.8.8'          # Target to check connectivity
        }]
        ),

        # 4. Diagnostic Aggregator
        Node(
            package='diagnostic_aggregator',
            executable='aggregator_node',
            name='diagnostic_aggregator',
            parameters=[config_path],
            output='screen'
        ),

        # 5. RQT Robot Monitor
        # This will open the GUI window automatically when you launch
        Node(
            package='rqt_robot_monitor',
            executable='rqt_robot_monitor',
            name='rqt_robot_monitor',
            output='screen'
        )
    ])
```

#### 4.6 Final Build Configuration

Ensure the CMakeLists.txt is updated to install the Python scripts and config files alongside the C++ executables.

**File: `CMakeLists.txt (Diagnostic Package)`**

```cpp
cmake_minimum_required(VERSION 3.8)
project(turtlebot3_navigation2)

#-----------------------------------------------------------------------------
# 1. FIND DEPENDENCIES
#-----------------------------------------------------------------------------
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(action_msgs REQUIRED)
find_package(diagnostic_updater REQUIRED)
find_package(diagnostic_msgs REQUIRED)

#-----------------------------------------------------------------------------
# 2. C++ EXECUTABLES (The Nodes)
#-----------------------------------------------------------------------------

#Controller Diagnostics Node
add_executable(controller_diagnostics_node src/controller_diagnostics_node.cpp)
ament_target_dependencies(controller_diagnostics_node
  rclcpp
  geometry_msgs
  action_msgs
  diagnostic_updater
  diagnostic_msgs
)

#Planner Diagnostics Node
add_executable(planner_diagnostics_node src/planner_diagnostics_node.cpp)
ament_target_dependencies(planner_diagnostics_node
  rclcpp
  diagnostic_updater
  diagnostic_msgs
)

#-----------------------------------------------------------------------------
# 3. INSTALLATION LOGIC
#-----------------------------------------------------------------------------

#A. Install C++ Binaries to lib/package_name
install(TARGETS
  controller_diagnostics_node
  planner_diagnostics_node
  DESTINATION lib/${PROJECT_NAME}
)

#B. Install Python Scripts (Network Monitor)
#This makes scripts/network_diagnostics.py.py an executable in your path
install(PROGRAMS
  scripts/network_diagnostics.py.py
  DESTINATION lib/${PROJECT_NAME}
)

#C. Install Launch and Config Directories
#This moves your .yaml and .launch.py files to the share/ directory
install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
)

#-----------------------------------------------------------------------------
# 4. EXPORT & FINALIZE
#-----------------------------------------------------------------------------
ament_export_dependencies(rclcpp rclpy diagnostic_updater)
ament_package()
```

#### 4.7 How to Run

Build the workspace: colcon build

Source the environment: source install/setup.bash

Launch the system:

```bash
ros2 launch turtlebot3_navigation2 aggregator.launch.py
```

### 5. Planner Assumptions & Limitations

- In this project, the default A\* planner provided by Navigation2 stack package named ***nav2_navfn_planner*** has not been used, instead a custom plugin package named **custom_a_star_planner** has been created that implements the A\* logic.
- The default A\* Global Planner provided by the Navigation2 stack has a functionality of continuously replanning the robot’s path as the robot keeps progressing towards its goal and its current position w.r.t the goal.
- However, in the Custom Global A\* Planner, this functionality of continuous replanning of robot’s path is not included. The path is calculated by the planner only once at the very start when the robot is at the starting position/node and the calculated path remains fixed for the rest of the journey until the robot reaches its intended goal.

### 6. Tunable Parameters And Their Impact

#### Changing the Default Global Planner to Custom A\* Planner

- In order to change the planner-plugin that is used by the Navigation2 stack’s `planner_server` node, firstly a new folder named `config` is created inside the **custom_a_star_planner** package and inside it the file named **waffle.yaml** which is copied directly from ***turtlebot3_ws/src/turtlebot3/turtlebot3_navigation2/param*** directory is pasted and renamed as ***custom_nav_params.yaml***.

    This is the default *.yaml* configuration file that the `turtlebot3/turtlebot3_navigation` package uses upon running the bash command for default navigation:

    ```
    ros2 launch turtlebot3_navigation2 navigation2.launch.py use_sim_time:=True map:=$HOME/map.yaml
    ```

- In the file ***custom_nav_params*** the field ***planner_server:GridBased:plugin*** is changed from its default value to `"custom_a_star_planner/AStarPlanner"`.

    ```yaml
    planner_server:
      ros__parameters:
        expected_planner_frequency: 0.0
        planner_plugins: ["GridBased"]
        GridBased:
          plugin: "custom_a_star_planner/AStarPlanner"   # custom A* class
    ```


#### Increasing the Accuracy of Reached Goal Location and Orientation

- To increase the accuracy of the location and orientation that the robot will reach after achieving its goal, the field values of `controller_server:ros__parameters:goal_checker:xy_goal_tolerance` and `controller_server:ros__parameters:goal_checker:yaw_goal_tolerance`
fields in the ***custom_nav_params.yaml*** file are changed from their default values (both 0.25) to 0.1.

    ```yaml
    controller_server:
      ros__parameters:
        goal_checker:
          stateful: true
          plugin: "nav2_controller::SimpleGoalChecker"
          xy_goal_tolerance: 0.1    # CHANGED
          yaw_goal_tolerance: 0.1   # CHANGED
    ```


#### Emulating the Stuck Robot Condition

- In order to emulate the stuck robot condition, make the following changes in the ***custom_nav_params.yaml*** file:

    ```yaml
    local_costmap:
        local_costmap:
            # robot_radius: 0.15 # original
            robot_radius: 0.5
            plugins: ["obstacle_layer", "voxel_layer", "inflation_layer"]
            inflation_layer:
                plugin: "nav2_costmap_2d::InflationLayer"
                # inflation_radius: 0.5 # original
                inflation_radius: 8.0
                # cost_scaling_factor: 5.0 #original
                cost_scaling_factor: 0.1
    ```

#### 1. `inflation_radius: 8.0`

This defines the **physical distance** (in meters) from an obstacle where the costmap starts increasing the "cost" of moving.

- **What 8.0 means:** You have told the robot that every single obstacle has an "aura" of **8 meters** around it.
- **The Effect:** Even if a wall is far away, the robot will see the area within 8 meters of that wall as a potential risk.
- **The Practical Result:** In a standard room, an 8-meter radius is **massive**. Since most rooms aren't 16 meters wide, your entire local costmap will likely be "filled" with inflation costs. The robot may struggle to find any "free space" to move because it thinks every square inch of the room is "near" an obstacle.

---

#### 2. `cost_scaling_factor: 0.1`

This controls **how fast the danger decreases** as the robot moves away from an obstacle. It defines the "slope" of the mountain.

- **How the math works:** The cost at a specific cell is calculated using a decay function: exp(−1.0⋅cost_scaling_factor⋅(distance−inscribed_radius)).
- **What 0.1 means:** A **lower** value (like 0.1) makes the cost decay **very slowly**.
- **The Effect:** Usually, this value is around 5.0 or 10.0 to make the "danger" drop off quickly once the robot is a safe distance away. By setting it to 0.1, you have created a very "gentle slope." Even at 5 meters away from a wall, the cost will still be significantly high.
- **The Practical Result:** The robot will be extremely "shy." It won't just avoid hitting a wall; it will try to stay as far away as humanly possible, even if it means taking a massive detour or failing to fit through a wide doorway.

---

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 31 — ROS2 Actions (C++)](31_ROS2_Actions_Cpp.md) | [Next Lesson: Chapter 33 — Understanding ROS2 Diagnostics →](33_Understanding_ROS2_Diagnostics.md)

