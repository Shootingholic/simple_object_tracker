FROM osrf/ros:jazzy-desktop AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies, OpenCV, X11, and Video4Linux utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip \
    python3-opencv \
    libopencv-dev \
    v4l-utils \
    x11-apps \
    ros-jazzy-cv-bridge \
    ros-jazzy-sensor-msgs \
    ros-jazzy-rosidl-default-generators \
    ros-jazzy-rosidl-default-runtime \
    && rm -rf /var/lib/apt/lists/*

# Set up ROS 2 workspace
WORKDIR /ros2_ws/src/simple_object_track

# Copy source code into workspace
COPY . .

WORKDIR /ros2_ws

# Build ROS 2 workspace
RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --symlink-install --packages-select simple_object_track

# Automatically source ROS 2 environment for interactive bash sessions
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "if [ -f /ros2_ws/install/setup.bash ]; then source /ros2_ws/install/setup.bash; fi" >> /root/.bashrc

# Copy and configure entrypoint
COPY ros_entrypoint.sh /ros_entrypoint.sh
RUN chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
