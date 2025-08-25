from collections import defaultdict

import geopandas as gpd
import logging
from shapely.geometry import LineString
from .classes import Trail, CuttingPoint  # Adjust relative import if needed
from .map_utils import *
logger = logging.getLogger(__name__)

# ----------------------------- #
# MAIN LOGIC
# ----------------------------- #
#on peut pas remplacer all_cutting_points par une utilisation de dict_cp_on_trails ?

def initialize_cutting_points(trails_dict, roads_gdf, threshold):
    """                                                                                    
    Compute cutting points for all trails and build a graph-like structure between them.

    Parameters:
        trails_dict (dict): {trail: []}
        roads_gdf (GeoDataFrame): Road network
        threshold (float): Distance threshold for connecting trail endpoints

    Returns:
        trails_dict (dict): {trail: list of CuttingPoint}
    """
    all_cutting_points = set()

    # 1. Create and connect cutting points
    for trail in trails_dict.keys():
        create_cutting_points(trail, roads_gdf, trails_dict, all_cutting_points, threshold)

    # 2. Sort cutting points along each trail
    for trail in trails_dict.keys():
        order_cutting_points_along_trail(trail, trails_dict)

    logger.debug(f"Total cutting points created: {sum(len(cps) for cps in trails_dict.values())}")
    return trails_dict

# ----------------------------- #
# INTERNAL HELPERS
# ----------------------------- #

def create_cutting_points(trail, roads_gdf, trails_dict, all_cutting_points, threshold):
    """
    For both endpoints of a trail, find/create cutting points and connect to nearby trails.
    """
    endpoints=[]
    for endpoint in trail.endpoints():
        cp = find_or_create_cutting_point(all_cutting_points, endpoint, trail, trails_dict, roads_gdf)
        endpoints.append(cp)
    connect_to_neighbors(trail, all_cutting_points, endpoints, trails_dict, threshold, roads_gdf)
    
    
def find_or_create_cutting_point(all_cutting_points, point_geom, trail, trails_dict, roads_gdf):
    """
    Reuse an existing cutting point if close enough, otherwise create and register a new one.
    """
    for cp in all_cutting_points:
        if cp.geom.distance(point_geom) < 0.2:
            trails_dict[trail].append(cp)
            return cp  # Reuse existing

    # Otherwise create new
    new_cp = CuttingPoint(geom=point_geom, roads=roads_gdf)
    trails_dict[trail].append(new_cp)
    all_cutting_points.add(new_cp)
    return new_cp

def connect_to_neighbors(trail, all_cutting_points, endpoints, trails_dict, threshold, roads_gdf):
    """
    Search for nearby trails to each endpoint and establish bidirectional neighbor connections 
    via cutting points.

    Parameters:
        trail (Trail): The current trail being processed.
        all_cutting_points (set): Global set of unique CuttingPoint instances.
        endpoints (list): List of CuttingPoint objects (usually 2, start and end).
        trails_dict (dict): Dictionary {Trail: list of CuttingPoints}.
        threshold (float): Maximum distance for neighbor search.
        roads_gdf (GeoDataFrame): Road network (used when creating new CuttingPoints).
    """
    # Step 1: Filter other trails (exclude the current one)
    other_trails = {t: cps for t, cps in trails_dict.items() if t != trail}

    # Step 2: Create GeoDataFrame for spatial queries
    if not other_trails:
        return  # nothing to connect to

    other_gdf = gpd.GeoDataFrame({
        "trail_obj": list(other_trails.keys()),
        "geometry": [t.geom for t in other_trails.keys()]
    }, crs=TARGET_CRS)

    # Step 3: For each endpoint, look for nearby trails and create mutual connections
    for endpoint in endpoints:
        other_gdf["dist"] = other_gdf.geometry.distance(endpoint.geom)
        nearby = other_gdf[other_gdf["dist"] < threshold]

        for _, row in nearby.iterrows():
            neighbor_trail = row["trail_obj"]

            # Project the endpoint onto the neighbor trail to create a CuttingPoint
            proj_dist = neighbor_trail.geom.project(endpoint.geom)
            neighbor_pt = neighbor_trail.geom.interpolate(proj_dist)

            # Find or create the corresponding CuttingPoint on the neighbor trail
            neighbor_endpoint = find_or_create_cutting_point(
                all_cutting_points, neighbor_pt, neighbor_trail, trails_dict, roads_gdf
            )

            # Initialize dict_neighbors if missing
            if not hasattr(endpoint, "dict_neighbors"):
                endpoint.dict_neighbors = defaultdict(list)
            if not hasattr(neighbor_endpoint, "dict_neighbors"):
                neighbor_endpoint.dict_neighbors = defaultdict(list)

            # Add bidirectional references
            if neighbor_endpoint not in endpoint.dict_neighbors:
                endpoint.dict_neighbors[neighbor_endpoint] = []
            if trail not in endpoint.dict_neighbors[neighbor_endpoint]:
                endpoint.dict_neighbors[neighbor_endpoint].append(neighbor_trail)

            if endpoint not in neighbor_endpoint.dict_neighbors:
                neighbor_endpoint.dict_neighbors[endpoint] = []
            if neighbor_trail not in neighbor_endpoint.dict_neighbors[endpoint]:
                neighbor_endpoint.dict_neighbors[endpoint].append(trail)


def order_cutting_points_along_trail(trail, trails_dict):
    """
    Sort the cutting points along the trail geometry.
    """
    def proj_dist(cp):
        return trail.geom.project(cp.geom)
    trails_dict[trail].sort(key=proj_dist)
