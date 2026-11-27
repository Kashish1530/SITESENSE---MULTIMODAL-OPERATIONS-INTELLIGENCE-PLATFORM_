from typing import List, Dict

def yolo_to_xyxy(yolo_det: List[float], img_w: int, img_h: int) -> Dict:
    """
    Input: [class_id, x_center, y_center, width, height, confidence] (Normalized 0.0-1.0)
    Output: Dictionary with absolute pixel coordinates and meta info.
    """
    class_id, x_c, y_c, w, h, conf = yolo_det
    
    # Denormalize to frame dimensions
    x_mid = x_c * img_w
    y_mid = y_c * img_h
    box_w = w * img_w
    box_h = h * img_h
    
    x1 = int(max(0, x_mid - (box_w / 2.0)))
    y1 = int(max(0, y_mid - (box_h / 2.0)))
    x2 = int(min(img_w, x_mid + (box_w / 2.0)))
    y2 = int(min(img_h, y_mid + (box_h / 2.0)))
    
    return {
        "class_id": int(class_id),
        "confidence": float(conf),
        "bbox": [x1, y1, x2, y2]
    }