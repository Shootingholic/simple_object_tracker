cmake_minimum_required(VERSION 3.8)
project(simple_object_track)

# Find Build Dependencies
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# ----------------------------------------------------
# 1. Custom ROS 2 Message Generation
# (Do NOT use SKIP_INSTALL so python msg bindings get installed)
# ----------------------------------------------------
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/ObjectState.msg"
)

# ----------------------------------------------------
# 2. Install Python Tracker Module via CMake Rules
# (Installs tracker.py into site-packages alongside generated msg)
# ----------------------------------------------------
ament_get_python_install_dir(PYTHON_INSTALL_DIR)

install(
  FILES
    simple_object_track/__init__.py
    simple_object_track/tracker.py
  DESTINATION "${PYTHON_INSTALL_DIR}/${PROJECT_NAME}"
)

# ----------------------------------------------------
# 3. C++ Webcam Publisher Node
# ----------------------------------------------------
add_executable(webcam_publisher_node src/webcam_publisher_node.cpp)
ament_target_dependencies(webcam_publisher_node
  rclcpp
  sensor_msgs
  cv_bridge
  OpenCV
)

install(TARGETS
  webcam_publisher_node
  DESTINATION lib/${PROJECT_NAME}
)

rosidl_get_typesupport_target(cpp_typesupport_target ${PROJECT_NAME} "rosidl_typesupport_cpp")
target_link_libraries(webcam_publisher_node "${cpp_typesupport_target}")

# ----------------------------------------------------
# 4. Install Executable Python Tracker Script
# ----------------------------------------------------
install(PROGRAMS
  ${PROJECT_NAME}/image_tracker_node.py
  DESTINATION lib/${PROJECT_NAME}
  RENAME image_tracker_node
)

# ----------------------------------------------------
# 5. Unit Testing Setup
# ----------------------------------------------------
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)
  find_package(ament_cmake_pytest REQUIRED)

  ament_add_gtest(test_webcam_publisher test/test_webcam_publisher.cpp)
  ament_add_pytest_test(test_tracker test/test_tracker.py)
endif()

ament_package()
