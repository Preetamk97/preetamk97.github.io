# Chapter 3 — Some Basic Terminologies & Features of ROS2

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 2 — Environment Setup](02_Environment_Setup.md) | [Next Lesson: Chapter 4 — Setting Up a ROS2 Workspace (for both C++ & Python) →](04_Setting_Up_a_ROS2_Workspace.md)

---

Before we start writing any code, it helps to get comfortable with a few core ideas and words that you will keep running into throughout this course. None of these are hard to understand — think of this chapter as learning the "vocabulary" of ROS 2 before we start building things with it.

- **Hardware Abstraction** — ROS 2 sits between your code and the actual hardware (motors, sensors, cameras, and so on). Instead of writing separate code for every different piece of hardware, ROS 2 gives you a common way to talk to all of them. This is what "hardware abstraction" means: you don't need to worry about the low-level details of a specific device — ROS 2 handles that for you.
- **Low Level Device Control** — This is the flip side of hardware abstraction. Somewhere underneath all the abstraction, something still has to talk directly to the motors and sensors at a very basic, low level. ROS 2 provides the tools to do this cleanly, so your device-specific code stays separate from your higher-level robot logic.
- **Data Distribution Service (DDS)** — DDS is the technology that lets different parts of your robot (called "nodes," explained below) talk to each other. Think of it as a messaging system running in the background. It decides how data gets sent from one node to another, and it does this reliably and quickly. DDS also lets you add security, so if you need to keep the data you're sending private, you can.
- **Nodes** — A node is simply a small program that does one specific job. For example, one node might read data from a camera, another might control the wheels, and another might plan a path. These nodes talk to each other using DDS.
- **Ways nodes talk to each other over DDS:**
    1. **Publisher-Subscriber Model** — One node (the **publisher**) sends out data as a **message**, and any other node that wants that data (a **subscriber**) can simply listen for it. The data travels over something called a **topic**, which you can picture as a named channel or pipe. Nodes don't need to know about each other directly — they just publish or subscribe to the same topic name. This lets nodes exchange information without being directly connected.
    2. **Service Model** — Here, one node (the **service server**) offers to do something for other nodes on request. A **service client** sends a single request, the server does the work, and then sends back a single response. This is useful when you need a quick "ask and get an answer" kind of interaction, rather than a constant stream of data.
    3. **Actions** — Actions are for tasks that take some time to finish, like moving a robot arm to a position. The **action client** sends a goal to the **action server**, and while the server works on it, it keeps sending back **feedback** messages so the client knows how things are progressing. Once the task is done, the server sends back a final **result**.
- **Node Parameters** — Parameters are simply settings that a node can read and change while it's running, without needing to stop and restart it. They're stored by the ROS 2 parameter system. You can use parameters to make your node's behavior configurable — for example, changing a robot's speed limit or a sensor's threshold without touching the code itself.
- **Bag Files** — A bag file is basically a recording. It stores the messages that were sent over one or more topics so you can play them back later, exactly as they happened. This is extremely useful for testing — instead of running your robot again to get real data, you can just replay a bag file. Bag files can record from many topics at once, and when played back, they publish the recorded data on those same topic names again.
- **Packages** — A package is how ROS 2 organizes your code. It's a folder that bundles together everything a certain piece of functionality needs — the code itself, along with any data, configuration, or documentation it depends on. Because everything is neatly packaged together, you (or anyone else) can easily share it and reuse it in other projects.
- **Cross-Platform Support** — ROS 2 isn't locked to one operating system. It can run on Linux, Windows, and macOS.
- **Easy Integration with ROS 1** — If you or your team already have projects built in ROS 1, ROS 2 makes it possible to connect and work alongside them, instead of forcing a complete rewrite.

## ROS Simulation and Visualization Overview

Besides letting nodes talk to each other, the ROS ecosystem also comes with tools for simulating robots and visualizing their data. We'll go into these in much more detail later in the course — for now, here's a quick introduction so you know they exist.

### Simulation

- **Gazebo** — Gazebo is a free robot simulator that works together with ROS. It can simulate a robot's position and behavior as if it were a real, physical robot, and it even includes virtual sensors that generate realistic sensor data. This means you can test your robot's code inside a simulation before ever touching real hardware. Gazebo has since partnered with Ignition Robotics, which led to the newer Ignition Gazebo simulation engine.

    Website: [http://gazebosim.org/](http://gazebosim.org/)

### Visualization

- ***RViz***

    RViz is a 3D visualization tool that also connects with ROS data. It lets you see your robot's sensor data and helps with tasks like localization, especially when working with a simulated robot.

    Website: [https://index.ros.org/p/rviz2/](https://index.ros.org/p/rviz2/)

- ***RQT***

    RQT is a plugin-based graphical interface for ROS. It comes with many useful plugins out of the box — a topic publisher, an image viewer, a parameter editor, a node graph viewer, and more. Some features overlap with what RViz offers, so you'll likely end up using both depending on the situation.

    Website: [http://wiki.ros.org/rqt](http://wiki.ros.org/rqt)

## Difference Between ROS 2 and ROS 1

Instead of simply patching the older ROS 1 system, the ROS developers decided to redesign it from the ground up to fix a number of long-standing problems. Below are some of the biggest changes that anyone coming from ROS 1 will notice.

### A More Decentralized Way of Communicating

One of the biggest changes in ROS 2 is switching to DDS for sending data. In ROS 1, there used to be a central "ROS Master" (roscore) and a parameter server that every node had to register with. In ROS 2, there's no such central authority — every node can operate independently.

### Security Options for Topics

This was a big win for anyone using ROS with private or sensitive data. ROS 2 lets developers set up secure keys for their nodes, so topics and their data can't be discovered or read by anyone who doesn't have the right keys.

### Launch Files Got a Rework

In ROS 1, launch files were written in XML. In ROS 2, they're written in Python instead, using the `roslaunch` Python module. The overall idea — organizing arguments, nodes, and so on — is still the same, just expressed in Python now.

### Bag Files Got a Rework Too

Bag files still work the same way conceptually, but now the data is saved into SQLite database files. There's also a default ROS 2 topic that tracks parameter change events, so your bag files can now capture parameter changes as well.

### Official Support for Actions

Actions existed in ROS 1, but only as an external library called `actionlib`. In ROS 2, actions are a first-class feature with their own dedicated tools and terminal commands.

### Cross-Platform Support

ROS 2 made a big leap by officially supporting Windows and macOS, not just Linux. There are still some platform-specific quirks to iron out, but this opened ROS up to a lot more developers who aren't necessarily using Linux.

### Compatibility with ROS 1

ROS 2 comes with a ROS 1 bridge tool, which lets you build new projects in ROS 2 while still being able to work with systems you've already built in ROS 1.

---

[← Back to Contents](00_Contents.md) | [← Previous Lesson: Chapter 2 — Environment Setup](02_Environment_Setup.md) | [Next Lesson: Chapter 4 — Setting Up a ROS2 Workspace (for both C++ & Python) →](04_Setting_Up_a_ROS2_Workspace.md)
