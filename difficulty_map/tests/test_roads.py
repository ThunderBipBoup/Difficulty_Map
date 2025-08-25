import unittest
import geopandas as gpd
from shapely.geometry import LineString, Point

from difficulty_map.source.roads import dist_on_road

class DummyCuttingPoint:
    def __init__(self, geom):
        self.geom = geom

class TestDistOnRoad(unittest.TestCase):

    def setUp(self):
        # Simple straight road from (0, 0) to (100, 0)
        road = LineString([(0, 0), (100, 0)])
        self.roads = gpd.GeoDataFrame(geometry=[road], crs="EPSG:32632")

        # CuttingPoint near (50, 10)
        self.cp = DummyCuttingPoint(Point(50, 10))
        self.start = Point(0, 0)

    def test_dist_on_road(self):
        dist = dist_on_road(self.roads, self.cp, self.start)
        self.assertGreater(dist, 0)
        self.assertLess(dist, 100)

if __name__ == '__main__':
    unittest.main()
