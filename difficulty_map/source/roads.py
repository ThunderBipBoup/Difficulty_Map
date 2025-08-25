import logging
import math

import geopandas as gpd
from shapely.geometry import LineString, Point

logger = logging.getLogger(__name__)
"""
def map_of_roads (roads_gdf: gpd.GeoDataFrame, starting_point: Point):
    distances = roads_gdf.geometry.distance(starting_point.geom)
    closest_idx = distances.idxmin()
    road_geom = roads_gdf.loc[closest_idx].geometry
        
    if not isinstance(road_geom, LineString):
            logger.warning(f"Unexpected geometry type for closest road: {type(road_geom)}")
            return float('inf')

    # Project points onto the road
    dist_start_point = road_geom.project(starting_point)
    
    for road in roads : 
        coords = list(road.geom.coords)
        current_dist,max_dist= Point(coords[0]), Point(coords[-1]) #end points of the road
    
        while current_dist < max_dist:
            next_dist = min(current_dist + dist_step, max_dist)
            segment = LineString([
                road_geom.interpolate(current_dist),
                road_geom.interpolate(next_dist)
                ])
            total_dist += segment.length
            current_dist = next_dist

            return total_dist
    
    """


def dist_on_road(
    roads_gdf: gpd.GeoDataFrame, cp, road_starting_point: Point = Point(820000, 5139000)
) -> float:
    """
    Compute the distance along the nearest road from a given cutting point (cp)
    to a fixed road starting point, by interpolating the geometry in small steps.

    Parameters:
        roads_gdf (GeoDataFrame): GeoDataFrame of road geometries.
        cp (CuttingPoint): Custom point class with attribute .geom (shapely Point).
        road_starting_point (Point): Starting reference point on the road.

    Returns:
        float: Approximate road distance between cp and road_starting_point.
    """
    try:
        # Find closest road geometry
        distances = roads_gdf.geometry.distance(cp.geom)
        closest_idx = distances.idxmin()
        road_geom = roads_gdf.loc[closest_idx].geometry

        if not isinstance(road_geom, LineString):
            logger.warning(
                "Unexpected geometry type for closest road: %s", type(road_geom)
            )
            return float("inf")

        # Project points onto the road
        dist_cp = road_geom.project(cp.geom)
        dist_start_point = road_geom.project(road_starting_point)

        min_dist = min(dist_cp, dist_start_point)
        max_dist = max(dist_cp, dist_start_point)

        dist_step = 50  # meters
        total_dist = 0
        current_dist = min_dist

        while current_dist < max_dist:
            next_dist = min(current_dist + dist_step, max_dist)
            segment = LineString(
                [road_geom.interpolate(current_dist), road_geom.interpolate(next_dist)]
            )
            total_dist += segment.length
            current_dist = next_dist

        return total_dist

    except Exception as e:
        logger.error("Error in dist_on_road():%s",e)
        return float("inf")


def create_tab_dist_on_roads(graph):
    tab_dist_on_roads = []
    for cp in graph.nodes:
        if not math.isinf(cp.dist_on_roads):
            tab_dist_on_roads.append(cp.dist_on_roads)
    return tab_dist_on_roads
