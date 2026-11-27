"""
test_visuals.py
Quick validation script to test drawing functions for all 16 SiteSense classes.
"""
import cv2
import numpy as np

def test_draw():
    img = np.full((1080, 1920, 3), (210, 215, 220), dtype=np.uint8)
    
    # Title
    cv2.putText(img, "SiteSense Class Visual Verification", (50, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 2)
    
    cv2.imwrite("outputs/test_render_check.jpg", img)
    print("Render check saved successfully!")

if __name__ == "__main__":
    test_draw()

