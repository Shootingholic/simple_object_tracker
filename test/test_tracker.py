# test/test_tracker.py
import cv2
import numpy as np
import pytest
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
