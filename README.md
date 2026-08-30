# Quickstart Commands
1. Allow X11 Host Display Access (WSL Terminal)
Before launching, execute this in your WSL terminal so OpenCV windows can display on Windows:


```Bash
xhost +local:docker
```
2. Build and Launch Container
```Bash
# 1. Build Docker image
docker compose build

# 2. Run container interactively
docker compose run --rm ros2_tracker
```
3. Run Nodes Inside Container
Once inside the container shell:

Terminal 1 (Publisher):

```Bash
ros2 run simple_object_track webcam_publisher_node --ros-args --params-file /ros2_ws/src/simple_object_track/config/webcam_param.yaml
```
Terminal 2 (Python Tracker Node with Trackbars):
Open a second terminal into the running container

```Bash
docker exec -it ros2_object_tracker bash
```

and run:

```Bash
ros2 run simple_object_track image_tracker_node
```
## Hardware Documentation & Device Troubleshooting

How to Identify the Host Webcam Device

- In WSL/Linux Host: Run the Video4Linux tool to list connected video devices:

```Bash
v4l2-ctl --list-devices
```
Or list system character devices:

```Bash
ls -l /dev/video*
```
- From Windows (PowerShell via usbipd):

```PowerShell
usbipd list
```
What to Change if the Camera Device Path Differs
If your camera attaches as /dev/video2 instead of /dev/video0:

Update docker-compose.yml:
Change the devices mapping block:

```YAML
devices:
  - "/dev/video2:/dev/video2"
  - "/dev/video3:/dev/video3"
```
Update ROS 2 Parameter Configuration (config/params.yaml):
Update device_path:


```YAML
webcam_publisher_node:
  ros__parameters:
    device_path: "/dev/video2"
    width: 640
    height: 480
    fps: 30.0
```
