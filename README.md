# Simple Object Track (ROS 2 Jazzy)

A modular ROS 2 package designed for real-time webcam video stream publishing and color-based object tracking. Built with C++ for high-performance frame publishing and Python for dynamic computer vision tracking.

---

## 1. Project Overview

This ROS 2 package provides a webcam-to-tracker pipeline:
1. **Webcam publisher (`webcam_publisher_node`)**: Captures V4L2 camera frames in C++ and publishes `sensor_msgs/msg/Image` on `/camera/image_raw`. It requests MJPEG, retries camera reconnection up to ten times by default, and limits output dimensions to the configured size.
2. **HSV tracker (`image_tracker_node`)**: Converts frames to HSV, filters for a selected color, and publishes up to a configurable number of contour detections per frame. Red, green, and blue presets and custom HSV trackbars are available.

### Quick Start with Docker
The tracker opens an OpenCV window, so a working desktop display is required. On Linux with X11, allow the local Docker client to connect before starting:
```bash
xhost +local:docker
```
Build the image and start the container service:
```bash
docker compose build
docker compose up -d ros2_tracker
```
In a first terminal, open a shell in the container and start the webcam publisher:
```bash
docker compose exec ros2_tracker bash
ros2 run simple_object_track webcam_publisher_node --ros-args --params-file /ros2_ws/install/simple_object_track/share/simple_object_track/config/webcam_param.yaml
```
In a second terminal, open another shell and start the tracker with its shipped settings:
```bash
docker compose exec ros2_tracker bash
ros2 run simple_object_track image_tracker_node --ros-args --params-file /ros2_ws/install/simple_object_track/share/simple_object_track/config/tracker_param.yaml
```
Stop the container with `docker compose down`. See [Hardware Documentation & Device Troubleshooting](#5-hardware-documentation--device-troubleshooting) if the camera is not visible inside Docker or WSL.
---

## 2. ROS Distribution & Languages

- **ROS Distribution:** ROS 2 Jazzy Jalisco
- **Languages:**
  - **C++ (C++17):** `webcam_publisher_node` (OpenCV, `rclcpp`, `cv_bridge`)
  - **Python (3.12+):** `image_tracker_node`, `tracker` module (`rclpy`, OpenCV, NumPy)

---

## 3. Configuration & Parameter Management

Both nodes accept ROS 2 parameters. The shipped parameter files are installed under `share/simple_object_track/config/`; edit them in the source tree and rebuild the package (or rebuild the Docker image with `docker compose build`) to include config changes.

### Available Parameters
| Parameter | Node | Node default / shipped YAML | Description |
| :--- | :--- | :--- | :--- |
| `device_path` | Webcam | `/dev/video0` / `/dev/video0` | V4L2 device path visible to the node. |
| `width` | Webcam | `640` / `640` | Requested output width in pixels; maximum 1920. |
| `height` | Webcam | `480` / `480` | Requested output height in pixels; maximum 1080. |
| `fps` | Webcam | `30.0` / `10.0` | Requested capture and publish rate; must be greater than 0 and at most 1000. |
| `frame_id` | Webcam | `camera_frame` / `camera_optical_frame` | Frame identifier placed in each image header. |
| `max_retries` | Webcam | `10` / Not set (uses node default) | Reconnection attempts before the publisher exits. |
| `min_object_area_percent` | Tracker | `0.1` / `0.1` | Minimum contour area as a percentage of the frame area; range 0-100. |
| `max_tracked_objects` | Tracker | `5` / `5` | Maximum detections per frame; range 1-10. |

### Overriding Configuration at Launch

**Via Command Line:**
```bash
ros2 run simple_object_track webcam_publisher_node --ros-args \
  -p device_path:="/dev/video2" \
  -p width:=1280 \
  -p height:=720 \
  -p fps:=60.0
```

Edit `config/tracker_param.yaml` to configure the tracker persistently. Parameters can also be overridden from the command line:
```bash
ros2 run simple_object_track image_tracker_node --ros-args \
  --params-file /ros2_ws/install/simple_object_track/share/simple_object_track/config/tracker_param.yaml \
  -p min_object_area_percent:=0.2 -p max_tracked_objects:=3
```
## 4. Custom Message Definition
| Topic | Type | Behavior |
| :--- | :--- | :--- |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | BGR camera frames from the webcam publisher. |
| `/tracker/objects` | `simple_object_track/msg/ObjectStateArray` | Up to `max_tracked_objects` detections per frame, ordered by contour area, largest first. The list may be empty. |
| `/tracker/object_state` | `simple_object_track/msg/ObjectState` | Backward-compatible single result: the largest detection, or `is_visible=false` when none are found. |

Each detection's `confidence` is its contour area divided by frame area, not a probability. Array positions are not persistent object IDs across frames; objects are independently detected in each image.

### Message Definition (`msg/ObjectState.msg`)
```text
int32 center_x      # X-coordinate of the object centroid in pixels
int32 center_y      # Y-coordinate of the object centroid in pixels
bool is_visible     # Whether the single-result topic contains a detection
float32 confidence  # Contour area divided by frame area [0.0 - 1.0]
```

### Message Definition (`msg/ObjectStateArray.msg`)
```text
simple_object_track/ObjectState[] objects
```
To inspect the message definition in your terminal:
```bash
ros2 interface show simple_object_track/msg/ObjectState
ros2 interface show simple_object_track/msg/ObjectStateArray
```

## 5. Hardware Documentation & Device Troubleshooting
Work through these checks in order. The webcam publisher reads `device_path` from `config/webcam_param.yaml` (default `/dev/video0`), and Docker can only see devices explicitly passed through to the container.

### 1. Check Linux Device Detection
On the Linux host or inside WSL, run:
```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```
If `v4l2-ctl` is missing on Ubuntu/Debian, install it with `sudo apt install v4l-utils`.
If no video device appears, reconnect the camera and check that the host/WSL kernel recognizes it before troubleshooting ROS or Docker. In WSL2, follow the USB/IP steps below. Device numbers can change after reconnecting, so use the path shown by these commands.

### 2. Check Host Permissions
Inspect the device owner, group, and your current groups:
```bash
id -nG
stat -c '%A %U %G %n' /dev/video0
```
If the device belongs to the `video` group and your Linux account is not in that group, add it and then fully log out and back in (or restart the WSL distribution):
```bash
sudo usermod -aG video "$USER"
```
Check permissions again after logging back in. Do not use `chmod 666` or `chmod 777` as a workaround; those changes are overly broad and are usually reset when the device is recreated.

### 3. Attach a USB Camera to WSL2
In an elevated Windows PowerShell, find and bind the camera, then attach it to WSL:
```powershell
usbipd list
usbipd bind --busid <BUS_ID>
usbipd attach --wsl --busid <BUS_ID>
```
Then, inside WSL, confirm that `/dev/video*` appears and run `v4l2-ctl --list-devices`. If the camera is not listed, check `usbipd list` in Windows and reattach it; attaching it to WSL makes it unavailable to Windows applications while attached.

### 4. Pass the Correct Device into Docker
The current `docker-compose.yml` passes only `/dev/video0` and `/dev/video1`. If the camera appears under another path, add a `devices` mapping for it. For example, to use host `/dev/video2` at the same path in the container, add:
```yaml
devices:
  - "/dev/video2:/dev/video2"
```
Then set `device_path` to `/dev/video2` in `config/webcam_param.yaml` (or map the host device to `/dev/video0` and keep the default). Recreate the container after changing the mapping. The existing container runs as root; if you change it to run as a non-root user or use rootless Docker and get `Permission denied`, also grant that container user the device's numeric group ID and verify the Docker device access rules. Host `video` group membership by itself does not pass an unmapped device into the container.

For a non-root container user, export the device GID on the host and add `group_add` under the service in `docker-compose.yml`:
```bash
export VIDEO_GID="$(stat -c '%g' /dev/video0)"
```
```yaml
group_add:
  - "${VIDEO_GID}"
```
After the container starts, repeat `ls -l /dev/video*` and `v4l2-ctl --list-devices` inside it. If the device exists on the host but not in the container, correct the Compose `devices` mapping; if it exists but access is denied, check the container user, group ID, and Docker device rules.

### 5. Check for Busy or Unsupported Devices
Confirm the selected device exists and supports video capture:
```bash
v4l2-ctl --device=/dev/video0 --all
v4l2-ctl --device=/dev/video0 --list-formats-ext
```
This node requests MJPEG (`MJPG`). If the camera does not list MJPEG or the node opens but produces empty frames, try a supported camera/mode or update the capture format in the node. If another application is using the camera, identify it with `fuser -v /dev/video0` (`psmisc`) and close that application before retrying.

### 6. Confirm ROS Is Receiving Frames
Launch the publisher with the webcam parameter file and check its logs for camera initialization or reconnect messages:
```bash
ros2 run simple_object_track webcam_publisher_node --ros-args --params-file /ros2_ws/install/simple_object_track/share/simple_object_track/config/webcam_param.yaml
```
In another sourced ROS terminal, check whether images are arriving:
```bash
ros2 topic hz /camera/image_raw
```
If no rate is reported, recheck `device_path`, host detection/permissions, and the Docker mapping. If frames arrive but tracking does not, camera permissions are no longer the likely issue; check the image and tracker color/area settings instead.
## 6. Project Structure

```PlaintText
simple_object_track/
├── README.md                     # Project Description
├── CMakeLists.txt                # Build configuration (C++, Python modules, ROS msgs)
├── package.xml                   # Package manifest & dependencies
├── .pre-commit-config.yaml       # Linting & formatting git hook setup
├── docker-compose.yml            # Build configuration for docker image
├── Dockerfile                    # DockerFile for deploy
├── ros_entrypoint.sh             # Script for enviroment settings
├── config/
│   ├── tracker_param.yaml        # Tracker parameters
│   └── webcam_param.yaml         # Parameters for web camera (resolution, frequency, device name)
├── msg/
│   ├── ObjectState.msg           # Single detection message
│   └── ObjectStateArray.msg      # Per-frame detection list
├── simple_object_track/
│   ├── image_tracker_node.py     # Executable ROS 2 Python tracking node
│   ├── __init__.py
│   └── tracker.py                # Core HSV computer vision algorithm
├── src/
│   └── webcam_publisher_node.cpp # Executable C++ camera publisher node
└── test/
    ├── test_tracker.py           # Pytest unit tests for HSV vision tracker
    └── test_webcam_publisher.cpp # GTest unit tests for camera node configurations
```

## 7. Pre-commit Hook Setup

This project enforces code style and formatting standards (Ruff for Python, Clang-Format for C++) via pre-commit.

### Installation

```Bash
# 1. Install pre-commit tool via pip
pip install pre-commit

# 2. Install Git hook scripts into .git/hooks/
pre-commit install
```

### Running Hooks Manually
To check all files across the repository prior to committing:
```Bash
pre-commit run --all-files
```
## 8. Automated Unit Testing
Tracker tests use synthetic images and need no physical camera. ROS integration tests exercise image subscription and both result topics when the ROS environment and generated messages are available. The C++ publisher tests validate camera parameter bounds.
### Run Tests inside Workspace
```Bash
# 1. Build the package with test targets enabled
colcon build --packages-select simple_object_track --cmake-args -DBUILD_TESTING=ON

# 2. Source workspace environment
source install/setup.bash

# 3. Execute all unit tests (Pytest + GTest)
colcon test --packages-select simple_object_track

# 4. View detailed results
colcon test-result --all --verbose
```

## 9. GitHub Actions CI/CD
Pull requests targeting `main` and pushes to `main` or a `v*` version tag build and test the package on ROS 2 Jazzy. After successful checks, pushes publish the Docker image to GitHub Container Registry (`ghcr.io/shootingholic/simple_object_tracker`): `main` and `latest` for main-branch pushes, and the matching version tag for version releases.

GitHub Container Registry packages are private by default. Change the package visibility in GitHub settings if the image should be publicly pullable.

To pull a published image:
```bash
docker pull ghcr.io/shootingholic/simple_object_tracker:latest
```

## 10. Tracking Approach & Limitations
### Computer Vision Pipeline
1. The BGR image is blurred and converted to HSV.
2. The selected Red, Green, or Blue preset filters the frame; Red uses two hue intervals to handle wraparound. Custom HSV lower/upper bounds can be tuned with the OpenCV trackbars.
3. Erosion and dilation reduce small mask noise. External contours below `min_object_area_percent` of the frame are discarded.
4. The largest qualifying contours, up to `max_tracked_objects`, are selected. Image moments provide each centroid; detections are returned largest-first and confidence is contour-area/frame-area.

## 11. Known Limitations & Intentional Shortcuts
- Lighting sensitivity: HSV thresholding can fail under strong shadows, reflections, or overexposure; tune the ranges for the environment.
- Touching or overlapping objects of the selected color may form one contour and be reported as one detection.
- The tracker processes one color range at a time and does not associate detections across frames. Array ordering is by size, not a stable object identity.
- The OpenCV preview and trackbars require a working graphical display (X11/Wayland, such as VcXsrv or WSLg).
