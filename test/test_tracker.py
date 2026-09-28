# test/test_tracker.py
import time

import cv2
import numpy as np
import pytest

try:
    import rclpy
    from cv_bridge import CvBridge
    from sensor_msgs.msg import Image

    from simple_object_track.image_tracker_node import ImageTrackerNode
    from simple_object_track.msg import ObjectState, ObjectStateArray

    ROS_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    rclpy = None
    CvBridge = None
    Image = None
    ImageTrackerNode = None
    ObjectState = None
    ObjectStateArray = None
    ROS_AVAILABLE = False

from simple_object_track.tracker import HSVObjectTracker


def test_normal_tracking_synthetic_blue_square():
    """Test normal tracking: detects a synthetic blue square and returns valid coordinates."""
    # Create a 400x400 black image
    img = np.zeros((400, 400, 3), dtype=np.uint8)

    # Draw a solid blue square centered at (200, 200)
    # BGR format: Blue = (255, 0, 0)
    cv2.rectangle(img, (150, 150), (250, 250), (255, 0, 0), -1)

    tracker = HSVObjectTracker()
    is_visible, cx, cy, conf = tracker.process_frame(img)

    assert is_visible is True
    assert pytest.approx(cx, abs=5) == 200
    assert pytest.approx(cy, abs=5) == 200
    assert conf > 0.0
    assert conf < 1.0


def test_minimum_object_area_is_resolution_independent():
    tracker = HSVObjectTracker(min_object_area_percent=0.5)

    for frame_size, square_size in ((400, 40), (800, 80)):
        img = np.zeros((frame_size, frame_size, 3), dtype=np.uint8)
        start = (frame_size - square_size) // 2
        cv2.rectangle(
            img,
            (start, start),
            (start + square_size, start + square_size),
            (255, 0, 0),
            -1,
        )

        is_visible, _, _, confidence = tracker.process_frame(img)

        assert is_visible is True
        assert confidence == pytest.approx(0.01, abs=0.002)


def test_minimum_object_area_percentage_filters_small_objects():
    tracker = HSVObjectTracker(min_object_area_percent=1.0)
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(img, (190, 190), (210, 210), (255, 0, 0), -1)

    is_visible, cx, cy, confidence = tracker.process_frame(img)

    assert is_visible is False
    assert (cx, cy, confidence) == (0, 0, 0.0)


def test_detects_multiple_objects_largest_first():
    tracker = HSVObjectTracker(min_object_area_percent=0.1)
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 150), (130, 230), (255, 0, 0), -1)
    cv2.rectangle(img, (350, 160), (410, 220), (255, 0, 0), -1)

    objects = tracker.process_objects(img)

    assert len(objects) == 2
    assert pytest.approx(objects[0][0], abs=5) == 90
    assert pytest.approx(objects[0][1], abs=5) == 190
    assert pytest.approx(objects[1][0], abs=5) == 380
    assert pytest.approx(objects[1][1], abs=5) == 190
    assert objects[0][2] > objects[1][2]


def test_detection_count_is_limited_and_legacy_api_returns_largest():
    tracker = HSVObjectTracker(max_tracked_objects=2)
    img = np.zeros((400, 600, 3), dtype=np.uint8)
    cv2.rectangle(img, (20, 150), (60, 190), (255, 0, 0), -1)
    cv2.rectangle(img, (200, 140), (280, 220), (255, 0, 0), -1)
    cv2.rectangle(img, (400, 150), (460, 210), (255, 0, 0), -1)

    objects = tracker.process_objects(img)
    is_visible, center_x, center_y, _ = tracker.process_frame(img)

    assert len(objects) == 2
    assert is_visible is True
    assert (center_x, center_y) == objects[0][:2]


@pytest.mark.parametrize("value", [0, 11, 1.5, True])
def test_invalid_max_tracked_objects(value):
    with pytest.raises(ValueError, match="max_tracked_objects"):
        HSVObjectTracker(max_tracked_objects=value)


@pytest.mark.parametrize("value", [-0.1, 100.1, float("nan")])
def test_invalid_minimum_object_area_percentage(value):
    with pytest.raises(ValueError, match="min_object_area_percent"):
        HSVObjectTracker(min_object_area_percent=value)


def test_no_object_detected():
    """Edge Case: Ensure node handles frames with no matching target color cleanly."""
    # Blank black image
    img = np.zeros((400, 400, 3), dtype=np.uint8)

    tracker = HSVObjectTracker()
    is_visible, cx, cy, conf = tracker.process_frame(img)

    assert is_visible is False
    assert cx == 0
    assert cy == 0
    assert conf == 0.0


def test_invalid_or_empty_image():
    """Edge Case: Handling empty or None frames raises ValueError."""
    tracker = HSVObjectTracker()

    with pytest.raises(ValueError, match="Invalid or empty frame provided."):
        tracker.process_frame(None)

    empty_img = np.array([], dtype=np.uint8)
    with pytest.raises(ValueError, match="Invalid or empty frame provided."):
        tracker.process_frame(empty_img)


def _solid_color_frame(color_bgr):
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(img, (150, 150), (250, 250), color_bgr, -1)
    return img


def test_color_presets_update_ranges_and_track_correctly():
    """Each preset should update HSV bounds and detect the matching object."""
    tracker = HSVObjectTracker()

    for color_name, color_bgr in {
        "RED": (0, 0, 255),
        "GREEN": (0, 255, 0),
        "BLUE": (255, 0, 0),
    }.items():
        tracker.set_color_preset(color_name)

        assert np.array_equal(
            tracker.lower_hsv, HSVObjectTracker.PRESETS[color_name][0]
        )
        assert np.array_equal(
            tracker.upper_hsv, HSVObjectTracker.PRESETS[color_name][1]
        )

        img = _solid_color_frame(color_bgr)
        is_visible, cx, cy, conf = tracker.process_frame(img)

        assert is_visible is True
        assert pytest.approx(cx, abs=5) == 200
        assert pytest.approx(cy, abs=5) == 200
        assert conf > 0.0


def test_red_wraparound_detection_handles_hue_transition():
    """Red detection should still work when the hue wraps from 179 to 0."""
    tracker = HSVObjectTracker()
    tracker.set_color_preset("RED")

    red_img = _solid_color_frame((0, 0, 255))
    is_visible, cx, cy, conf = tracker.process_frame(red_img)

    assert is_visible is True
    assert pytest.approx(cx, abs=5) == 200
    assert pytest.approx(cy, abs=5) == 200
    assert conf > 0.0


def test_custom_hsv_range_supports_nonpreset_detection():
    """Custom HSV bounds should work for manually tuned targets."""
    tracker = HSVObjectTracker()
    tracker.lower_hsv = np.array([90, 120, 50], dtype=np.uint8)
    tracker.upper_hsv = np.array([140, 255, 255], dtype=np.uint8)

    blue_img = _solid_color_frame((255, 0, 0))
    is_visible, cx, cy, conf = tracker.process_frame(blue_img)

    assert is_visible is True
    assert pytest.approx(cx, abs=5) == 200
    assert pytest.approx(cy, abs=5) == 200
    assert conf > 0.0


def test_unknown_preset_does_not_change_tracker_state():
    """Unknown presets should be ignored instead of mutating active HSV thresholds."""
    tracker = HSVObjectTracker()
    original_lower = tracker.lower_hsv.copy()
    original_upper = tracker.upper_hsv.copy()

    tracker.set_color_preset("MAGENTA")

    assert np.array_equal(tracker.lower_hsv, original_lower)
    assert np.array_equal(tracker.upper_hsv, original_upper)


@pytest.mark.skipif(
    not ROS_AVAILABLE,
    reason="ROS runtime and generated message modules are not available",
)
def test_tracker_node_publishes_object_state_for_camera_image(monkeypatch):
    """Integration test for the camera-image to ObjectState ROS flow when the target is visible."""
    monkeypatch.setattr(cv2, "namedWindow", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "createTrackbar", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "getTrackbarPos", lambda *args, **kwargs: 3)
    monkeypatch.setattr(cv2, "putText", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "circle", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "imshow", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "waitKey", lambda *args, **kwargs: 0)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda *args, **kwargs: None)

    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()

    publisher_node = rclpy.create_node("camera_publisher_tester")
    tracker_node = ImageTrackerNode()
    listener_node = rclpy.create_node("tracker_state_listener")
    received = {}

    def on_state(msg):
        received["state"] = msg

    def on_objects(msg):
        received["objects"] = msg

    listener_node.create_subscription(
        ObjectState,
        "/tracker/object_state",
        on_state,
        10,
    )
    listener_node.create_subscription(
        ObjectStateArray,
        "/tracker/objects",
        on_objects,
        10,
    )
    publisher = publisher_node.create_publisher(Image, "/camera/image_raw", 10)

    img = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.rectangle(img, (150, 150), (250, 250), (255, 0, 0), -1)
    cv2.rectangle(img, (300, 150), (360, 210), (255, 0, 0), -1)
    bridge = CvBridge()
    frame_msg = bridge.cv2_to_imgmsg(img, encoding="bgr8")

    publisher.publish(frame_msg)

    deadline = time.time() + 3.0
    while time.time() < deadline and not {"state", "objects"}.issubset(received):
        rclpy.spin_once(tracker_node, timeout_sec=0.05)
        rclpy.spin_once(listener_node, timeout_sec=0.05)
        rclpy.spin_once(publisher_node, timeout_sec=0.01)

    try:
        state = received["state"]
    finally:
        tracker_node.destroy_node()
        listener_node.destroy_node()
        publisher_node.destroy_node()
        rclpy.shutdown()

    assert state.is_visible is True
    assert pytest.approx(state.center_x, abs=8) == 200
    assert pytest.approx(state.center_y, abs=8) == 200
    assert state.confidence > 0.0
    assert len(received["objects"].objects) == 2
    assert pytest.approx(received["objects"].objects[0].center_x, abs=8) == 200
    assert pytest.approx(received["objects"].objects[1].center_x, abs=8) == 330


@pytest.mark.skipif(
    not ROS_AVAILABLE,
    reason="ROS runtime and generated message modules are not available",
)
def test_tracker_node_publishes_not_visible_for_empty_frame(monkeypatch):
    """Integration test for the camera-image to ObjectState ROS flow when no target is visible."""
    monkeypatch.setattr(cv2, "namedWindow", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "createTrackbar", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "getTrackbarPos", lambda *args, **kwargs: 3)
    monkeypatch.setattr(cv2, "putText", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "circle", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "imshow", lambda *args, **kwargs: None)
    monkeypatch.setattr(cv2, "waitKey", lambda *args, **kwargs: 0)
    monkeypatch.setattr(cv2, "destroyAllWindows", lambda *args, **kwargs: None)

    if rclpy.ok():
        rclpy.shutdown()
    rclpy.init()

    publisher_node = rclpy.create_node("camera_publisher_no_target_tester")
    tracker_node = ImageTrackerNode()
    listener_node = rclpy.create_node("tracker_no_target_listener")
    received = {}

    def on_state(msg):
        received["state"] = msg

    listener_node.create_subscription(
        ObjectState,
        "/tracker/object_state",
        on_state,
        10,
    )
    publisher = publisher_node.create_publisher(Image, "/camera/image_raw", 10)

    img = np.zeros((400, 400, 3), dtype=np.uint8)
    bridge = CvBridge()
    frame_msg = bridge.cv2_to_imgmsg(img, encoding="bgr8")

    publisher.publish(frame_msg)

    deadline = time.time() + 3.0
    while time.time() < deadline and "state" not in received:
        rclpy.spin_once(tracker_node, timeout_sec=0.05)
        rclpy.spin_once(listener_node, timeout_sec=0.05)
        rclpy.spin_once(publisher_node, timeout_sec=0.01)

    try:
        state = received["state"]
    finally:
        tracker_node.destroy_node()
        listener_node.destroy_node()
        publisher_node.destroy_node()
        rclpy.shutdown()

    assert state.is_visible is False
    assert state.center_x == 0
    assert state.center_y == 0
    assert state.confidence == 0.0
