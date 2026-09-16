# Chapter 32 — Project 4 — TurtleBot3 Navigation with a Custom A\* Planner

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

This launches the full Navigation2 stack — Gazebo continues running the simulated TurtleBot3, while RViz opens automatically (as part of the `navigation2.launch.py` bringup) so you can set a `2D Pose Estimate` and a `Nav2 Goal Pose` and watch the custom A\* planner's path get visualized on the map.

### 4. Planner Assumptions & Limitations

- In this project, the default A\* planner provided by Navigation2 stack package named ***nav2_navfn_planner*** has not been used, instead a custom plugin package named **custom_a_star_planner** has been created that implements the A\* logic.
- The default A\* Global Planner provided by the Navigation2 stack has a functionality of continuously replanning the robot’s path as the robot keeps progressing towards its goal and its current position w.r.t the goal.
- However, in the Custom Global A\* Planner, this functionality of continuous replanning of robot’s path is not included. The path is calculated by the planner only once at the very start when the robot is at the starting position/node and the calculated path remains fixed for the rest of the journey until the robot reaches its intended goal.

### 5. Tunable Parameters And Their Impact

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
