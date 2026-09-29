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
        self.mask_window_name = "HSV Calibration Mask"
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.namedWindow(self.mask_window_name, cv2.WINDOW_NORMAL)
        self.active_preset_mode = 3
        self.latest_frame = None
        self.calibration_status = (
            "Choose Custom (0), then click the target to sample HSV."
        )

        # 0: Custom, 1: Red, 2: Green, 3: Blue
        cv2.createTrackbar(
            "Preset 0:Custom 1:Red 2:Green 3:Blue",
            self.window_name,
            3,
            3,
            nothing,
        )

        cv2.createTrackbar("Low H", self.window_name, 100, 179, nothing)
        cv2.createTrackbar("Low S", self.window_name, 150, 255, nothing)
        cv2.createTrackbar("Low V", self.window_name, 50, 255, nothing)
        cv2.createTrackbar("High H", self.window_name, 140, 179, nothing)
        cv2.createTrackbar("High S", self.window_name, 255, 255, nothing)
        cv2.createTrackbar("High V", self.window_name, 255, 255, nothing)
        cv2.setMouseCallback(self.window_name, self._on_frame_click)

        self.get_logger().info("Tracker initialized with Red/Green/Blue color presets.")

    def _on_frame_click(self, event, x, y, flags, parameter):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if self.active_preset_mode != 0:
            self.calibration_status = "Select Custom (0) before sampling a target."
            return

        if self.latest_frame is None:
            return

        y_min = max(0, y - 4)
        y_max = min(self.latest_frame.shape[0], y + 5)
        x_min = max(0, x - 4)
        x_max = min(self.latest_frame.shape[1], x + 5)
        patch = self.latest_frame[y_min:y_max, x_min:x_max]
        sample_bgr = np.median(patch, axis=(0, 1)).astype(np.uint8)
        sample_hsv = cv2.cvtColor(
            np.array([[sample_bgr]], dtype=np.uint8), cv2.COLOR_BGR2HSV
        )[0, 0]

        margins = np.array([8, 70, 70], dtype=np.int16)
        sample = sample_hsv.astype(np.int16)
        lower = np.maximum(sample - margins, 0).astype(np.uint8)
        upper = np.minimum(sample + margins, [179, 255, 255]).astype(np.uint8)
        self.tracker.lower_hsv = lower
        self.tracker.upper_hsv = upper

        for name, value in zip(("Low H", "Low S", "Low V"), lower):
            cv2.setTrackbarPos(name, self.window_name, int(value))
        for name, value in zip(("High H", "High S", "High V"), upper):
            cv2.setTrackbarPos(name, self.window_name, int(value))

        self.calibration_status = (
            f"Sampled H:{sample_hsv[0]} S:{sample_hsv[1]} V:{sample_hsv[2]}. "
            "Tune sliders to remove background or recover missed target areas."
        )

    def image_callback(self, msg):
        if not rclpy.ok():
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        except CvBridgeError as e:
            self.get_logger().error(f"cv_bridge error: {e}")
            return

        preset_mode = cv2.getTrackbarPos(
            "Preset 0:Custom 1:Red 2:Green 3:Blue", self.window_name
        )
        self.active_preset_mode = preset_mode
        self.latest_frame = frame.copy()

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

        mask = self.tracker.create_mask(frame)
        detections = self.tracker.process_objects(frame, mask=mask)
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

        # Keep calibration guidance visible over the live camera feed.
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 126), (24, 32, 38), -1)
        cv2.putText(
            frame,
            f"HSV CALIBRATION | Mode: {active_color_label} | Detections: {len(detections)}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (90, 220, 240),
            1,
            cv2.LINE_AA,
        )
        guide_lines = (
            "1. Select a preset, or choose Custom (0).",
            "2. In Custom mode, click the target to sample its starting HSV range.",
            "3. In the mask window, target pixels should be white; background black.",
            "4. Tune Low/High H, S, V sliders. Press Q or Esc to quit.",
            self.calibration_status,
        )
        for index, line in enumerate(guide_lines, start=1):
            cv2.putText(
                frame,
                line,
                (10, 26 + index * 19),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.43,
                (225, 230, 232),
                1,
                cv2.LINE_AA,
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
        cv2.imshow(self.mask_window_name, mask)
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
