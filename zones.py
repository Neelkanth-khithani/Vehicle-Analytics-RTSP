import json
from shapely.geometry import Point, Polygon

def load_zones(filepath="zones.json"):
    with open(filepath, 'r') as f:
        data = json.load(f)
    polygons = []
    for zone in data.get('zones', []):
        polygons.append(Polygon(zone))
    return polygons

def check_point_in_zones(point, polygons):
    p = Point(point)
    for i, poly in enumerate(polygons):
        if poly.contains(p):
            return i
    return -1