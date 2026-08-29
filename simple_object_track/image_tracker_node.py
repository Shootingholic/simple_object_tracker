#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from sensor_msgs.msg import Image
from simple_object_track.msg import ObjectState
from cv_bridge import CvBridge, CvBridgeError
import cv2
import numpy as np


def nothing(x):
    pass


class ImageTrackerNode(Node):
    def __init__(self):
        super().__init__("image_tracker_node")

        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            Image, "/camera/image_raw", self.image_callback, 10
        )

        self.state_pub = self.create_publisher(ObjectState, "/tracker/object_state", 10)

        self.window_name = "Object Tracker Controls"
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)

        # Trackbar initializations
        cv2.createTrackbar("L - H", self.window_name, 100, 179, nothing)
        cv2.createTrackbar("L - S", self.window_name, 150, 255, nothing)
        cv2.createTrackbar("L - V", self.window_name, 50, 255, nothing)
        cv2.createTrackbar("U - H", self.window_name, 140, 179, nothing)
        cv2.createTrackbar("U - S", self.window_name, 255, 255, nothing)
        cv2.createTrackbar("U - V", self.window_name, 255, 255, nothing)

        self.get_logger().info(
            "Tracker initialized cleanly. Publishing to /tracker/object_state"
        )

    def image_callback(self, msg):
        if not rclpy.ok():
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f"cv_bridge conversion error: {e}")
            return

        # Always construct valid default state message (is_visible=False)
        state_msg = ObjectState()
        state_msg.center_x = 0
        state_msg.center_y = 0
        state_msg.is_visible = False
        state_msg.confidence = 0.0

        # Read Trackbars
        l_h = cv2.getTrackbarPos("L - H", self.window_name)
        l_s = cv2.getTrackbarPos("L - S", self.window_name)
        l_v = cv2.getTrackbarPos("L - V", self.window_name)
        u_h = cv2.getTrackbarPos("U - H", self.window_name)
        u_s = cv2.getTrackbarPos("U - S", self.window_name)
        u_v = cv2.getTrackbarPos("U - V", self.window_name)

        lower_hsv = np.array([l_h, l_s, l_v])
        upper_hsv = np.array([u_h, u_s, u_v])

        # Filter Mask
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_hsv, upper_hsv)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(
            mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Process object detection
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)

            if radius > 10:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])

                    # Update message fields when visible
                    state_msg.center_x = center_x
                    state_msg.center_y = center_y
                    state_msg.is_visible = True

                    frame_area = frame.shape[0] * frame.shape[1]
                    state_msg.confidence = float(
                        min(M["m00"] / (frame_area * 0.2), 1.0)
                    )

                    cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)
                    cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)

        # Guarantee message publication on EVERY frame callback regardless of detection
        self.state_pub.publish(state_msg)

        # GUI display rendering
        cv2.imshow(self.window_name, frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = ImageTrackerNode()

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
