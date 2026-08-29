#include <chrono>
#include <memory>
#include <string>

#include "cv_bridge/cv_bridge.hpp"
#include "opencv2/opencv.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"

using namespace std::chrono_literals;

class WebcamPublisher : public rclcpp::Node {
public:
  WebcamPublisher() : Node("webcam_publisher"), retry_count_(0) {
    // Declare parameters with default values
    this->declare_parameter<std::string>("device_path", "/dev/video0");
    this->declare_parameter<int>("width", 640);
    this->declare_parameter<int>("height", 480);
    this->declare_parameter<double>("fps", 30.0);
    this->declare_parameter<std::string>("frame_id", "camera_frame");
    this->declare_parameter<int>("max_retries", 10);

    // Retrieve parameters
    device_path_ = this->get_parameter("device_path").as_string();
    width_ = this->get_parameter("width").as_int();
    height_ = this->get_parameter("height").as_int();
    fps_ = this->get_parameter("fps").as_double();
    frame_id_ = this->get_parameter("frame_id").as_string();
    max_retries_ = this->get_parameter("max_retries").as_int();

    publisher_ = this->create_publisher<sensor_msgs::msg::Image>(
        "/camera/image_raw", 10);

    // Initial webcam setup
    if (!init_camera()) {
      RCLCPP_ERROR(this->get_logger(),
                   "Initial connection to camera '%s' failed. Will attempt "
                   "reconnects in main loop.",
                   device_path_.c_str());
    }

    // Set up timer loop based on FPS
    auto interval = std::chrono::duration<double>(1.0 / fps_);
    timer_ = this->create_wall_timer(
        std::chrono::duration_cast<std::chrono::milliseconds>(interval),
        std::bind(&WebcamPublisher::timer_callback, this));
  }

  ~WebcamPublisher() override {
    if (cap_.isOpened()) {
      cap_.release();
    }
  }

private:
  bool init_camera() {
    if (cap_.isOpened()) {
      cap_.release();
    }

    cap_.open(device_path_, cv::CAP_V4L2);
    if (!cap_.isOpened()) {
      return false;
    }

    // Force MJPEG to prevent select() timeouts on USB/WSL2
    cap_.set(cv::CAP_PROP_FOURCC, cv::VideoWriter::fourcc('M', 'J', 'P', 'G'));
    cap_.set(cv::CAP_PROP_FRAME_WIDTH, width_);
    cap_.set(cv::CAP_PROP_FRAME_HEIGHT, height_);
    cap_.set(cv::CAP_PROP_FPS, fps_);

    retry_count_ = 0; // Reset retry counter on successful open
    RCLCPP_INFO(this->get_logger(),
                "Webcam initialized successfully [%s @ %dx%d %.1f FPS]",
                device_path_.c_str(), width_, height_, fps_);
    return true;
  }

  void timer_callback() {
    // If device lost or not open, attempt reconnect with backoff
    if (!cap_.isOpened()) {
      retry_count_++;
      if (retry_count_ > max_retries_) {
        RCLCPP_FATAL(this->get_logger(),
                     "Exceeded maximum camera reconnect attempts (%d). Exiting "
                     "process with code 1.",
                     max_retries_);
        rclcpp::shutdown();
        std::exit(1);
      }

      RCLCPP_WARN(this->get_logger(),
                  "Camera device unavailable. Reconnect attempt %d/%d...",
                  retry_count_, max_retries_);

      // Wait 2 seconds before retry (Backoff)
      std::this_thread::sleep_for(2s);
      init_camera();
      return;
    }

    cv::Mat frame;
    cap_ >> frame;

    if (frame.empty()) {
      RCLCPP_WARN(this->get_logger(),
                  "Captured empty frame from webcam '%s'. Disconnecting device "
                  "to trigger re-init.",
                  device_path_.c_str());
      cap_.release();
      return;
    }

    // Convert OpenCV BGR Mat to ROS Image message
    std_msgs::msg::Header header;
    header.stamp = this->now();
    header.frame_id = frame_id_;

    sensor_msgs::msg::Image::SharedPtr msg =
        cv_bridge::CvImage(header, "bgr8", frame).toImageMsg();

    publisher_->publish(*msg);
  }

  cv::VideoCapture cap_;
  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;

  std::string device_path_;
  int width_;
  int height_;
  double fps_;
  std::string frame_id_;
  int max_retries_;
  int retry_count_;
};

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  auto node = std::make_shared<WebcamPublisher>();

  try {
    rclcpp::spin(node);
  } catch (const std::exception &e) {
    RCLCPP_ERROR(node->get_logger(), "Exception caught in main spin loop: %s",
                 e.what());
  }

  rclcpp::shutdown();
  return 0;
}
