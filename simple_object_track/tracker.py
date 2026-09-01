# simple_object_track/tracker.py
import cv2
import numpy as np


class HSVObjectTracker:
    # Preset HSV Color Ranges
    PRESETS = {
        "RED": (
            np.array([0, 120, 70], dtype=np.uint8),
            np.array([10, 255, 255], dtype=np.uint8),
        ),
        "GREEN": (
            np.array([36, 100, 100], dtype=np.uint8),
            np.array([86, 255, 255], dtype=np.uint8),
        ),
        "BLUE": (
            np.array([100, 150, 50], dtype=np.uint8),
            np.array([140, 255, 255], dtype=np.uint8),
        ),
    }

    def __init__(self, lower_hsv=None, upper_hsv=None):
        self.lower_hsv = lower_hsv if lower_hsv is not None else self.PRESETS["BLUE"][0]
        self.upper_hsv = upper_hsv if upper_hsv is not None else self.PRESETS["BLUE"][1]

    def set_color_preset(self, color_name: str):
        color_key = color_name.upper()
        if color_key in self.PRESETS:
            self.lower_hsv, self.upper_hsv = self.PRESETS[color_key]

    def process_frame(self, frame):
        """Processes frame returning (is_visible, center_x, center_y, confidence)."""
        if frame is None or frame.size == 0:
            raise ValueError("Invalid or empty frame provided.")

        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        # Red wraps around HSV spectrum (0-10 and 170-180)
        if np.array_equal(self.lower_hsv, self.PRESETS["RED"][0]):
            mask1 = cv2.inRange(hsv, self.PRESETS["RED"][0], self.PRESETS["RED"][1])
            lower_red2 = np.array([170, 120, 70], dtype=np.uint8)
            upper_red2 = np.array([180, 255, 255], dtype=np.uint8)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, self.lower_hsv, self.upper_hsv)

        # Morphological Operations to elimate the minor noise in background
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        contours, _ = cv2.findContours(
            mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if len(contours) > 0:
            # Find the max area as the track object
            c = max(contours, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)

            if radius > 10:
                # Calculate center of mass of arbitrary shape
                M = cv2.moments(c)
                if M["m00"] != 0:
                    center_x = int(M["m10"] / M["m00"])
                    center_y = int(M["m01"] / M["m00"])
                    frame_area = frame.shape[0] * frame.shape[1]
                    confidence = float(min(M["m00"] / (frame_area * 0.2), 1.0))
                    return True, center_x, center_y, confidence

        return False, 0, 0, 0.0
