import logging
from collections import defaultdict

import geopandas as gpd

from difficulty_map.source.classes import CuttingPoint
from difficulty_map.source.map_utils import TARGET_CRS

logger = logging.getLogger(__name__)

# ----------------------------- #
# MAIN LOGIC
# ----------------------------- #


def build_cutting_points(trails_dict, roads_gdf, trails_threshold, 
                         roads_threshold):
    """
    Build and connect CuttingPoints across trails.

    Parameters
    ----------
    trails_dict : dict
        {Trail: []}, initially empty lists.
    roads_gdf : GeoDataFrame
        Road network used to attach CuttingPoints.
    trails_threshold : float
        Distance threshold for inter-trail connections.
    roads_threshold : float
        Maximum distance between a trail and a road for them to be considered connected
    Returns
    -------
    all_cutting_points : list
        List of all CuttingPoint instances.
    """

    all_cutting_points = set()

    for trail in trails_dict.keys():
        create_cutting_points(
            trail, roads_gdf, trails_dict, all_cutting_points, 
            trails_threshold, roads_threshold
        )

    for trail in trails_dict.keys():
        order_cutting_points_along_trail(trail, trails_dict)

    # Connect consecutive cutting points on each trail (intra-trail)
    for trail, cps in trails_dict.items():
        for i in range(len(cps) - 1):
            cp1, cp2 = cps[i], cps[i + 1]
            cp1.dict_neighbors[cp2].append(trail)
            cp2.dict_neighbors[cp1].append(trail)

    logger.info(f"Total cutting points created: {len(all_cutting_points)}")
    return list(all_cutting_points)


# ----------------------------- #
# INTERNAL HELPERS
# ----------------------------- #


def create_cutting_points(trail, roads_gdf, trails_dict, all_cutting_points, 
                          trails_threshold, roads_threshold):
    """
    For both endpoints of a trail, find/create cutting points and connect to 
    nearby trails.
    """
    endpoints = []
    for endpoint in trail.endpoints():
        cp = find_or_create_cutting_point(
            all_cutting_points, endpoint, trail, trails_dict, roads_gdf, 
            roads_threshold
        )
        endpoints.append(cp)
    connect_to_neighbors(
        trail, all_cutting_points, endpoints, trails_dict, trails_threshold, 
        roads_gdf, roads_threshold
    )


def find_or_create_cutting_point(
    all_cutting_points, point_geom, trail, trails_dict, roads_gdf,
    roads_threshold
):
    """
    Reuse an existing cutting point if close enough, otherwise create 
    and register a new one.
    """
    for cp in all_cutting_points:
        if cp.geom.distance(point_geom) < 0.2:
            trails_dict[trail].append(cp)
            return cp  # Reuse existing

    # Otherwise create new
    new_cp = CuttingPoint(geom=point_geom, roads=roads_gdf, 
                          roads_threshold=roads_threshold)
    trails_dict[trail].append(new_cp)
    all_cutting_points.add(new_cp)
    return new_cp


def connect_to_neighbors(
    trail, all_cutting_points, endpoints, trails_dict, trails_threshold, roads_gdf, 
    roads_threshold
):
    """
    Search for nearby trails to each endpoint and establish bidirectional 
    neighbor connections via cutting points.

    Parameters:
        trail: Trail
            The current trail being processed.
        all_cutting_points: set
            Global set of unique CuttingPoint instances.
        endpoints: list
            List of CuttingPoint objects (usually 2, start and end).
        trails_dict: dict
            Dictionary {Trail: list of CuttingPoints}.
        trails_threshold: float
            Maximum distance for neighbor search.
        roads_gdf: GeoDataFrame
            Road network (used when creating new CuttingPoints).
        roads_threshold : float
            Maximum distance between a trail and a road for them to be 
            considered connected.
    """
    # Exclude the current trail
    other_trails = {t: cps for t, cps in trails_dict.items() if t != trail}

    # Create GeoDataFrame for spatial queries
    if not other_trails:
        return  # nothing to connect to

    other_gdf = gpd.GeoDataFrame(
        {
            "trail_obj": list(other_trails.keys()),
            "geometry": [t.geom for t in other_trails.keys()],
        },
        crs=TARGET_CRS,
    )

    # For each endpoint, look for nearby trails and create mutual connections
    for endpoint in endpoints:
        other_gdf["dist"] = other_gdf.geometry.distance(endpoint.geom)
        nearby = other_gdf[other_gdf["dist"] < trails_threshold]

        for _, row in nearby.iterrows():
            neighbor_trail = row["trail_obj"]

            # Project the endpoint onto the neighbor trail to create a CuttingPoint
            proj_dist = neighbor_trail.geom.project(endpoint.geom)
            neighbor_pt = neighbor_trail.geom.interpolate(proj_dist)

            # Find or create the corresponding CuttingPoint on the neighbor trail
            neighbor_endpoint = find_or_create_cutting_point(
                all_cutting_points, neighbor_pt, neighbor_trail, trails_dict, roads_gdf, 
                roads_threshold
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
