# Simple Object Track (ROS 2 Jazzy)

A modular ROS 2 package designed for real-time webcam video stream publishing and color-based object tracking. Built with C++ for high-performance frame publishing and Python for dynamic computer vision tracking.

---

## 1. Project Overview

This project provides a complete ROS 2 computer vision pipeline consisting of:
1. **Webcam Publisher Node (`webcam_publisher_node`)**: A C++ node that captures video frames from a physical camera (or v4l2 loopback device) and streams them over a ROS 2 topic.
2. **Image Tracker Node (`image_tracker_node`)**: A Python node that subscribes to the video stream, isolates objects based on HSV color profiles (with convenient Red, Green, and Blue presets), and publishes object location metrics.
### Quickstart Commands
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

- Terminal 1 (Publisher):

```Bash
ros2 run simple_object_track webcam_publisher_node --ros-args --params-file /ros2_ws/install/simple_object_track/share/simple_object_track/config/webcam_param.yaml
```
- Terminal 2 (Python Tracker Node with Trackbars):
Open a second terminal into the running container
```Bash
docker exec -it ros2_object_tracker bash
```

and run:

```Bash
ros2 run simple_object_track image_tracker_node
```
To load the tracker settings from YAML:
```Bash
ros2 run simple_object_track image_tracker_node --ros-args --params-file /ros2_ws/install/simple_object_track/share/simple_object_track/config/tracker_param.yaml
```
---

## 2. ROS Distribution & Languages

- **ROS Distribution:** ROS 2 Jazzy Jalisco
- **Languages:**
  - **C++ (C++17):** `webcam_publisher_node` (OpenCV, `rclcpp`, `cv_bridge`)
  - **Python (3.12+):** `image_tracker_node`, `tracker` module (`rclpy`, OpenCV, NumPy)

---

## 3. Configuration & Parameter Management

You can adjust the camera device, resolution, and frame rate without modifying source code by setting ROS 2 parameters at runtime or modifying the launch file parameters.

### Available Parameters
| Parameter Name | Type | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `video_device` | `string` | `/dev/video0` | Linux V4L2 device index for the camera. |
| `frame_width` | `int` | `640` | Requested capture resolution width in pixels (maximum 1920). |
| `frame_height` | `int` | `480` | Requested capture resolution height in pixels (maximum 1080). |
| `fps` | `double` | `30.0` | Target publishing frame rate (Frames Per Second). |
| `min_object_area_percent` | `double` | `0.1` | Minimum detected contour area as a percentage of the image area (0-100). |

### Overriding Configuration at Launch

**Via Command Line:**
```bash
ros2 run simple_object_track webcam_publisher_node --ros-args \
  -p video_device:="/dev/video2" \
  -p frame_width:=1280 \
  -p frame_height:=720 \
  -p fps:=60.0
```

Edit `config/tracker_param.yaml` to change the tracker's minimum contour area percentage. The node accepts command-line overrides too:
```bash
ros2 run simple_object_track image_tracker_node --ros-args -p min_object_area_percent:=0.2
```
## 4. Custom Message Definition
The tracking results are broadcasted over the `/tracker/object_state` topic using the custom interface `simple_object_track/msg/ObjectState.`

### Message Definition (`msg/ObjectState.msg`)
```Plaintextint32
center_x            # X-coordinate of the detected object centroid (pixels)
int32 center_y      # Y-coordinate of the detected object centroid (pixels)
bool is_visible     # Flag set to true if a valid target is currently tracked
float32 confidence  # Detected contour area as a fraction of the frame [0.0 - 1.0]
```
To inspect the message definition in your terminal:
```Bash
ros2 interface show simple_object_track/msg/ObjectState
```

## 5. Hardware Documentation & Device Troubleshooting
When running inside Docker or WSL, ensuring proper camera permissions and device passthrough is critical.

### Camera Access Setup
#### 1. Grant Device Permissions:
Ensure your current Linux user belongs to the `video` group:
```Bash
sudo usermod -aG video $USER
```

#### 2. WSL2 USB Camera Passthrough (usbipd-win):

Attach your USB webcam to WSL2 from Windows
```PowerShell
usbipd list
usbipd attach --wsl --busid <BUS_ID>
```

#### 3. Verify Device Recognition:
Confirm `/dev/video0` (or similar) exists inside your terminal environment:
```Bash
ls -l /dev/video*
```
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
├── config
│   ├── tracker_param.yaml        # Tracker parameters
│   └── webcam_param.yaml         # Parameters for web camera (resolution, frequency, device name)
├── msg
│   └── ObjectState.msg           # Custom ROS 2 message specification
├── simple_object_track
│   ├── image_tracker_node.py     # Executable ROS 2 Python tracking node
│   ├── __init__.py
│   └── tracker.py                # Core HSV Computer Vision algorithm module
├── src
│   └── webcam_publisher_node.cpp # Executable C++ camera publisher node
└── test
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
Unit tests run independently of physical camera hardware using synthetic images and parameter verification mocks.
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
Alternatively, test Python logic directly:
```Bash
pytest test/test_tracker.py
```
## 9. Tracking Approach & Limitations
### Computer Vision Pipeline
1. Color Space Conversion: Input BGR frames are converted to the HSV (Hue, Saturation, Value) color space, which provides resilience against brightness fluctuations.
2. Preset Filtering: Includes built-in threshold ranges for Red (handles HSV hue wrapping around 0°/180°), Green, and Blue, plus dynamic slider adjustments.
3. Morphological Filtering: Erosion followed by dilation cleans up single-pixel noise and isolated reflections.
4. Centroid Estimation: Image spatial moments ($M_{00}, M_{10}, M_{01}$) are calculated on the maximum area contour to extract exact center coordinates ($C_x, C_y$).

## 10. Known Limitations & Intentional Shortcuts
- Lighting Sensitivity: Pure HSV thresholding remains sensitive to aggressive environmental shadow changes or extreme overexposure.Single
- Target Tracking: The tracker isolates only the single largest contour matching the selected color preset per frame. Multiple instances of the same color are ignored.
- GUI Trackbars depend on OpenCV X11 Display: The OpenCV imshow and trackbar user controls require an active X11/Wayland display output (e.g., VcXsrv or WSLg).
