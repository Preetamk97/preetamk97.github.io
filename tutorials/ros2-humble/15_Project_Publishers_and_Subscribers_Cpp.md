# Chapter 15 — Project 1 — Publishers & Subscribers (C++)

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 14 — ROS2 Interface Types](14_ROS2_Interface_Types.md) | [Next Lesson: Chapter 16 — Project 1 — Publishers & Subscribers (Python) →](16_Project_Publishers_and_Subscribers_Python.md)

---

## Problem Statement

For this project, let us consider a simple robot that has **4 wheels** and is moving at a **constant speed**.

For this robot, we are going to create 2 simple nodes.

The **first** node **publishes** the readings of a **tachometer sensor** ( which measures the **RPM** of the robot wheels - which can be any **constant** of your choice ) to a topic called **rpm**.

Now the **second** node subscribes to the **topic rpm** and calculates the **speed** of the moving robot based on the **rpm** values and the **diameter** of the robot **wheels** (which is another constant) - and publishes this result to another new topic named **speed(m/s).**

## **rpm_publisher.cpp** code:

```cpp
// Including the rclcpp library - for ros2 c++ functionality.
#include "rclcpp/rclcpp.hpp"
// Next we are importing the interface of the messages we are going to publish through this node.
#include "std_msgs/msg/float64.hpp"

#include "chrono"
#include "functional"

using namespace std::chrono_literals;

const double RPM_VALUE = 100.0;

class RpmPubNode : public rclcpp::Node
{
private:
    rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr rpm_publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    void publish_rpm()
    {
        auto rpm_value = std_msgs::msg::Float64();
        rpm_value.data = RPM_VALUE;
        rpm_publisher_->publish(rpm_value);
    }

public:
    RpmPubNode() : Node("rpm_pub_node")
    {
        rpm_publisher_ = this->create_publisher<std_msgs::msg::Float64>("rpm", 10);
        timer_ = this->create_wall_timer(1s, std::bind(&RpmPubNode::publish_rpm, this));
        std::cout<<"RPM Publisher Node Is Running..."<<std::endl;
    }
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<RpmPubNode>());
    rclcpp::shutdown();
    return 0;
}
```

## **rpm_subscriber.cpp** code:

```cpp
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/float64.hpp"

#include "iostream"
#include "math.h"  //For using the value of Pi - M_PI

const double wheel_radius = 12.5/100; //Converting 12.5cm to meters.  //float64 datatype is double in C++

class RpmSubNode : public rclcpp::Node
{
private:
    rclcpp::Subscription<std_msgs::msg::Float64>::SharedPtr rpm_subscriber_;
    rclcpp::Publisher<std_msgs::msg::Float64>::SharedPtr speed_publisher_;
    void calculate_and_pub_speed(const std_msgs::msg::Float64 &rpm_msg) const
    {
        auto speed_msg = std_msgs::msg::Float64();
        //Speed[m/s] = { RPM (rev/min) * Wheel_Circumference(meters/rev) } / 60 seconds
        speed_msg.data = (rpm_msg.data * 2 * M_PI * wheel_radius)/60;
        speed_publisher_->publish(speed_msg);
    }

public:
    RpmSubNode() : Node("rpm_sub_node")
    {
        rpm_subscriber_ = this->create_subscription<std_msgs::msg::Float64>(
            "rpm",
            10,
            std::bind(&RpmSubNode::calculate_and_pub_speed, this, std::placeholders::_1)
            );

        speed_publisher_ = this->create_publisher<std_msgs::msg::Float64>("speed", 10);

        std::cout<<"RPM Subscriber Node Is Running..."<<std::endl;
    }
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<RpmSubNode>());
    rclcpp::shutdown();

    return 0;
}
```

## Compiling And Executing The Nodes:

1. **Adding the newly created files to `CMakeLists.txt` file.**

    Add the following code to the **CMakeLists.txt** file of the **ros2_cpp_udemy_tutorial/src/udemy_ros2_pkg** package folder.

    ```c
    add_executable(rpm_publisher src/rpm_publisher.cpp)
    ament_target_dependencies(rpm_publisher rclcpp std_msgs)

    add_executable(rpm_subscriber src/rpm_subscriber.cpp)
    ament_target_dependencies(rpm_subscriber rclcpp std_msgs)

    install(TARGETS
    				publisher
    				subscriber
    				rpm_publisher
    				rpm_subscriber
    				DESTINATION lib/${PROJECT_NAME}
    )
    ```

2. **Compiling the Workspace.** Open a new terminal in the **ros2_cpp_udemy_tutorial** workspace and build the workspace by running the `colcon build` command from the terminal.
3. **To run the rpm_publisher node:**

    In the same terminal from the previous step, run the following commands:

    ```cpp
    source install/setup.bash
    ros2 run udemy_ros2_pkg rpm_publisher

    ```

4. **To see the rpm messages published by the rpm_publisher** open a **parallel terminal** and run the following commands:

    ```cpp
    ros2 topic echo rpm
    ```

5. **To run the rpm_subscriber node:**

    Open a new terminal in the **ros2_cpp_udemy_tutorial** workspace and run the following commands:

    ```cpp
    source install/setup.bash
    ros2 run udemy_ros2_pkg rpm_subscriber

    ```

6. **To see the speed messages published by the rpm_subscriber** open a **parallel terminal** and run the following commands:

    ```cpp
    ros2 topic echo speed
    ```


![Figure 1 — Project 1 — Publishers & Subscribers (C++)](images/image106.png)

![Figure 2 — Project 1 — Publishers & Subscribers (C++)](images/image107.png)

---

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 14 — ROS2 Interface Types](14_ROS2_Interface_Types.md) | [Next Lesson: Chapter 16 — Project 1 — Publishers & Subscribers (Python) →](16_Project_Publishers_and_Subscribers_Python.md)

