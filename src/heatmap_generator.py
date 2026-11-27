"""
heatmap_generator.py
Feature 3: Cumulative Traffic & Congestion Heatmap Generator.
Accumulates object footprint centers across all frames and blends a JET colormap overlay.
"""
import cv2
import numpy as np

class HeatmapGenerator:
    def __init__(self, width: int = 1280, height: int = 720):
        self.width = width
        self.height = height
        self.heatmap = np.zeros((height, width), dtype=np.float32)

    def update(self, tracked_objects: list):
        """Accumulates bottom-center ground positions for pedestrians and vehicles."""
        for obj in tracked_objects:
            x1, y1, x2, y2 = obj["bbox"]
            cx = int((x1 + x2) // 2)
            cy = int(y2)
            
            # Bound check
            if 0 <= cx < self.width and 0 <= cy < self.height:
                # Add Gaussian-like kernel around the ground point
                cv2.circle(self.heatmap, (cx, cy), 28, 1.0, -1)

    def generate(self, background_frame: np.ndarray = None) -> np.ndarray:
        """Generates color-mapped overlay blended with the base video frame."""
        # Normalize to 0-255
        if np.max(self.heatmap) > 0:
            norm = (self.heatmap / np.max(self.heatmap) * 255).astype(np.uint8)
        else:
            norm = self.heatmap.astype(np.uint8)

        # Apply Gaussian blur for smooth density gradients
        blurred = cv2.GaussianBlur(norm, (31, 31), 0)
        color_map = cv2.applyColorMap(blurred, cv2.COLORMAP_JET)

        if background_frame is not None:
            # Mask out cold zero-activity areas
            mask = blurred > 12
            output = background_frame.copy()
            output[mask] = cv2.addWeighted(background_frame, 0.45, color_map, 0.55, 0)[mask]
            return output
        return color_map
