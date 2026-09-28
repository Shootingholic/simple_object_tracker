#!/usr/bin/env python3
import cv2
from cv_bridge import CvBridge, CvBridgeError
import numpy as np
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Image
from simple_object_track.msg import ObjectState, ObjectStateArray
from simple_object_track.tracker import HSVObjectTracker


def nothing(x):
    pass


class ImageTrackerNode(Node):
    def __init__(self):
        super().__init__("image_tracker_node")

        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            # it is better to set the queue size to 1 to make sure we can get the latest frame.
            Image,
            "/camera/image_raw",
            self.image_callback,
            10,
        )
        self.state_pub = self.create_publisher(ObjectState, "/tracker/object_state", 10)
        self.objects_pub = self.create_publisher(
            ObjectStateArray, "/tracker/objects", 10
        )

        min_object_area_percent = self.declare_parameter(
            "min_object_area_percent", 0.1
        ).value
        max_tracked_objects = self.declare_parameter("max_tracked_objects", 5).value
        self.tracker = HSVObjectTracker(
            min_object_area_percent=min_object_area_percent,
            max_tracked_objects=max_tracked_objects,
        )

        self.window_name = "Object Tracker Controls"
        cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)

        # 0: Custom, 1: Red, 2: Green, 3: Blue
        cv2.createTrackbar(
            "Preset (0:Custom 1:R 2:G 3:B)", self.window_name, 3, 3, nothing
        )

        # Fine-tuning sliders
        cv2.createTrackbar("L - H", self.window_name, 100, 179, nothing)
        cv2.createTrackbar("L - S", self.window_name, 150, 255, nothing)
        cv2.createTrackbar("L - V", self.window_name, 50, 255, nothing)
        cv2.createTrackbar("U - H", self.window_name, 140, 179, nothing)
        cv2.createTrackbar("U - S", self.window_name, 255, 255, nothing)
        cv2.createTrackbar("U - V", self.window_name, 255, 255, nothing)

        self.get_logger().info("Tracker initialized with Red/Green/Blue color presets.")

    def image_callback(self, msg):
        if not rclpy.ok():
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f"cv_bridge error: {e}")
            return

        preset_mode = cv2.getTrackbarPos(
            "Preset (0:Custom 1:R 2:G 3:B)", self.window_name
        )

        if preset_mode == 1:
            self.tracker.set_color_preset("RED")
            active_color_label = "RED"
        elif preset_mode == 2:
            self.tracker.set_color_preset("GREEN")
            active_color_label = "GREEN"
        elif preset_mode == 3:
            self.tracker.set_color_preset("BLUE")
            active_color_label = "BLUE"
        else:
            # Custom HSV Trackbars
            l_h = cv2.getTrackbarPos("L - H", self.window_name)
            l_s = cv2.getTrackbarPos("L - S", self.window_name)
            l_v = cv2.getTrackbarPos("L - V", self.window_name)
            u_h = cv2.getTrackbarPos("U - H", self.window_name)
            u_s = cv2.getTrackbarPos("U - S", self.window_name)
            u_v = cv2.getTrackbarPos("U - V", self.window_name)

            self.tracker.lower_hsv = np.array([l_h, l_s, l_v], dtype=np.uint8)
            self.tracker.upper_hsv = np.array([u_h, u_s, u_v], dtype=np.uint8)
            active_color_label = "CUSTOM"

        detections = self.tracker.process_objects(frame)
        objects_msg = ObjectStateArray()
        objects_msg.objects = []
        for cx, cy, confidence in detections:
            state_msg = ObjectState()
            state_msg.center_x = cx
            state_msg.center_y = cy
            state_msg.is_visible = True
            state_msg.confidence = confidence
            objects_msg.objects.append(state_msg)
        self.objects_pub.publish(objects_msg)

        is_visible = bool(detections)
        if is_visible:
            cx, cy, conf = detections[0]
            state_msg = objects_msg.objects[0]
        else:
            cx, cy, conf = 0, 0, 0.0
            state_msg = ObjectState()
            state_msg.center_x = cx
            state_msg.center_y = cy
            state_msg.is_visible = False
            state_msg.confidence = conf
        self.state_pub.publish(state_msg)

        # Overlay Active Mode & Tracking Coordinates
        cv2.putText(
            frame,
            f"Mode: {active_color_label}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2,
        )

        for index, (cx, cy, conf) in enumerate(detections, start=1):
            cv2.circle(frame, (cx, cy), 5, (0, 0, 255), -1)
            cv2.putText(
                frame,
                f"{index}: ({cx}, {cy}) Conf: {conf:.2f}",
                (cx + 10, cy - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

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
