
import unittest
from ..source.cutting_points import *



class Test_initialize_cp (unittest.TestCase):
    def test_input_value(self):
        self.assertRaises(TypeError,initialize_cutting_points,True)
        

# === Tests ===
class TestInitializeCuttingPoints(unittest.TestCase):

    def setUp(self):
        self.trails_dict = {
            1: LineString([(0, 0), (10, 0)]),
            2: LineString([(10, 0), (20, 0)])
        }
        self.trails_gdf = gpd.GeoDataFrame({'geometry': list(self.trails_dict.values()),'id': list(self.trails_dict.keys())})
        self.roads_gdf = gpd.GeoDataFrame({'geometry': [LineString([(5, -5), (5, 5)])], 'id': [1]})

# 1. Checks that the function returns a structured dictionary {trail_id: list of CuttingPoint}.
    def test_return_structure(self):
        result = initialize_cutting_points(self.trails_dict, self.trails_gdf, self.roads_gdf)
        self.assertIsInstance(result, dict)                 # The result is a dict
        self.assertIn(1, result)                            # It does contain a key for ID 1
        self.assertIsInstance(result[1], list)              # The value associated with this key is a list
        
# 2. Check that each trail has at least one cutting point (or 2 if they don't connect)
    def test_cutting_points_exist(self):
        result = initialize_cutting_points(self.trails_dict, self.trails_gdf, self.roads_gdf)
        for trail_id in self.trails_dict:
            self.assertGreaterEqual(len(result[trail_id]), 1)


# 3. Check that the cutting points are ordered in the same direction as the LineString.
    def test_cutting_points_ordering(self):
        result = initialize_cutting_points(self.trails_dict, self.trails_gdf, self.roads_gdf)
        cp_list = result[1]
        distances = [self.trails_dict[1].project(cp.geom) for cp in cp_list]
        self.assertEqual(distances, sorted(distances))  # Cutting points are well sorted

# 4. Ensure that if two trail endpoints are very close (< 0.2 units), they share the same CuttingPoint.
    def test_reuse_cutting_point_when_close(self):
        # Trails with endpoints less than 0.2 units apart
        trails_dict = {
            1: LineString([(0, 0), (1, 0)]),
            2: LineString([(1, 0.1), (2, 0.1)])  # Endpoint close to trail 1 end
        }
        trails_gdf = gpd.GeoDataFrame({'id': [1, 2], 'geometry': list(trails_dict.values())})
        roads_gdf = gpd.GeoDataFrame({'geometry': []})

        result = initialize_cutting_points(trails_dict, trails_gdf, roads_gdf)

        cp1_end = result[1][-1]  # end of trail 1
        cp2_start = result[2][0]  # start of trail 2

        self.assertIs(cp1_end, cp2_start, "CuttingPoint should be reused for close endpoints")

# 5. Validate that trails whose endpoints are within the threshold distance become connected as neighbors.
    def test_connects_nearby_trails_within_threshold(self):
        trails_dict = {
            1: LineString([(0, 0), (5, 0)]),
            2: LineString([(5.1, 0), (10, 0)])  # Very close to end of trail 1
        }
        trails_gdf = gpd.GeoDataFrame({'id': [1, 2], 'geometry': list(trails_dict.values())})
        roads_gdf = gpd.GeoDataFrame({'geometry': []})

        result = initialize_cutting_points(trails_dict, trails_gdf, roads_gdf, threshold=1.0)

        cp1 = result[1][-1]  # end of trail 1
        cp2 = result[2][0]   # start of trail 2

        self.assertIn(cp2, cp1.dict_neighbors)
        self.assertIn(cp1, cp2.dict_neighbors)

# 6. Ensure that trails do not connect if they're farther than the threshold.
    def test_does_not_connect_trails_beyond_threshold(self):
        trails_dict = {
            1: LineString([(0, 0), (5, 0)]),
            2: LineString([(10, 0), (15, 0)])  # Far from trail 1
        }
        trails_gdf = gpd.GeoDataFrame({'id': [1, 2], 'geometry': list(trails_dict.values())})
        roads_gdf = gpd.GeoDataFrame({'geometry': []})

        result = initialize_cutting_points(trails_dict, trails_gdf, roads_gdf, threshold=3.0)

        cp1 = result[1][-1]  # end of trail 1
        cp2 = result[2][0]   # start of trail 2

        self.assertNotIn(cp2, cp1.dict_neighbors)
        self.assertNotIn(cp1, cp2.dict_neighbors)

# 7. 
    def test_shared_cutting_point(self):
        # Trail 1 goes from (0,0) to (1,0)
        # Trail 2 goes from (1,0) to (2,0)
        trails_dict = {
            1: LineString([(0, 0), (1, 0)]),
            2: LineString([(1, 0), (2, 0)])
        }
        trails_gdf = gpd.GeoDataFrame({
            'id': [1, 2],
            'geometry': [trails_dict[1], trails_dict[2]]
        })
        roads_gdf = gpd.GeoDataFrame(geometry=[])  # Empty roads for simplicity

        result = initialize_cutting_points(trails_dict, trails_gdf, roads_gdf)

        # Now check: one shared point between trail 1 and 2
        shared_points = set(result[1]) & set(result[2])
        self.assertEqual(len(shared_points), 1)
