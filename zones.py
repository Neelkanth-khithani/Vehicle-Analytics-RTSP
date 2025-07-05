import json
import os

def load_zones(zones_file):
    """Load zones from JSON file"""
    if os.path.exists(zones_file):
        try:
            with open(zones_file, 'r') as f:
                data = json.load(f)
                # Expecting data to be a dictionary with a 'zones' key
                # Each zone in the list should be an object: {'id': ..., 'name': ..., 'points': [...]}
                return data.get('zones', []) if isinstance(data.get('zones'), list) else []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading zones from {zones_file}: {e}")
            return []
    return []

def check_point_in_zones(point, zones_polygons_only):
    """
    Check if a point is inside any zone polygon using ray casting algorithm.
    zones_polygons_only is expected to be a list of raw polygon points: [[x1,y1], [x2,y2], ...]
    """
    def point_in_polygon(point, polygon):
        if len(polygon) < 3:
            return False
            
        x, y = point
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0]
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        else: # Horizontal line
                            xinters = p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    for i, polygon in enumerate(zones_polygons_only):
        if point_in_polygon(point, polygon):
            return i
    return -1
