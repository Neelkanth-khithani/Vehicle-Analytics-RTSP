import json
import os

def load_zones(zones_file):
    """
    Loads zone configurations from a specified JSON file.

    This function attempts to open and parse a JSON file at `zones_file`.
    It expects the JSON to contain a key 'zones' which is a list of zone configurations.
    If the file does not exist, or if there's a JSON decoding error or an IOError,
    it prints an error message and returns an empty list.

    Args:
        zones_file (str): The path to the JSON file containing zone data.

    Returns:
        list: A list of zone configurations, or an empty list if loading fails or the file is empty/malformed.
    """
    if os.path.exists(zones_file):
        try:
            with open(zones_file, 'r') as f:
                data = json.load(f)
                return data.get('zones', []) if isinstance(data.get('zones'), list) else []
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading zones from {zones_file}: {e}")
            return []
    return []

def check_point_in_zones(point, zones_polygons_only):
    """
    Checks if a given point lies within any of the provided polygonal zones.

    This function iterates through a list of zone polygons and uses the
    "ray casting" or "winding number" algorithm (implemented in `point_in_polygon`)
    to determine if the `point` (e.g., the centroid of a detected object) falls
    inside any of the polygons.

    Args:
        point (tuple): A tuple (x, y) representing the coordinates of the point to check.
        zones_polygons_only (list): A list of lists, where each inner list represents
                                    a polygon, and each element in the inner list is
                                    a tuple (px, py) of polygon vertex coordinates.

    Returns:
        int: The index of the first zone (polygon) that contains the point.
             Returns -1 if the point is not found within any zone.
    """
    def point_in_polygon(point, polygon):
        """
        Determines if a point is inside a polygon using the ray casting algorithm.

        Args:
            point (tuple): The (x, y) coordinates of the point.
            polygon (list): A list of (px, py) tuples representing the polygon's vertices.

        Returns:
            bool: True if the point is inside the polygon, False otherwise.
        """
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
                        else:
                            xinters = p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    for i, polygon in enumerate(zones_polygons_only):
        if point_in_polygon(point, polygon):
            return i
    return -1