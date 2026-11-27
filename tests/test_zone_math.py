"""
tests/test_zone_math.py
Unit tests for Shapely-based polygon containment and bottom-center ground contact points.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from shapely.geometry import Point, Polygon
from zone_engine import ZoneEngine

def test_ground_contact_point_calculation():
    # Bbox: [x1, y1, x2, y2]
    bbox = [100, 200, 300, 400]
    pt = ZoneEngine.get_ground_contact_point(bbox)
    
    assert isinstance(pt, Point)
    assert pt.x == 200.0  # (100 + 300) / 2
    assert pt.y == 400.0  # y2 bottom

def test_point_in_polygon_containment():
    # Box polygon: (800, 500) to (1400, 1080)
    coords = [[800, 500], [1400, 500], [1400, 1080], [800, 1080]]
    poly = Polygon(coords)
    
    # Point clearly inside
    pt_inside = Point(1000, 750)
    assert poly.contains(pt_inside) is True
    
    # Point outside
    pt_outside = Point(600, 750)
    assert poly.contains(pt_outside) is False
    
    # Upper-body overlap false alarm avoidance test:
    # A person standing at x=750, y=750 with wide shoulders/box extending into (850, 600)
    # Upper body enters x=850, but ground feet point is at x=750, outside the exit!
    ground_pt = Point(750, 750)
    assert poly.contains(ground_pt) is False

