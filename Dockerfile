FROM osrf/ros:jazzy-desktop AS ros_base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

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

# Build the package in a separate stage so source does not enter the final image.
FROM ros_base AS builder

WORKDIR /ros2_ws/src/simple_object_track
COPY . .

WORKDIR /ros2_ws

RUN . /opt/ros/jazzy/setup.sh && \
    colcon build --packages-select simple_object_track

FROM ros_base AS runtime

WORKDIR /ros2_ws
COPY --from=builder /ros2_ws/install /ros2_ws/install

# Automatically source ROS 2 environment for interactive bash sessions
RUN echo "source /opt/ros/jazzy/setup.bash" >> /root/.bashrc && \
    echo "if [ -f /ros2_ws/install/setup.bash ]; then source /ros2_ws/install/setup.bash; fi" >> /root/.bashrc

COPY ros_entrypoint.sh /ros_entrypoint.sh
RUN chmod +x /ros_entrypoint.sh

ENTRYPOINT ["/ros_entrypoint.sh"]
CMD ["bash"]
