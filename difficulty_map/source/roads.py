import logging
import geopandas as gpd
import networkx as nx
from shapely.geometry import LineString, Point

logger = logging.getLogger(__name__)


def dist_on_road(
    roads_gdf: gpd.GeoDataFrame,
    cp,
    road_starting_point: Point = Point(820000, 5139000),
) -> float:
    """
    Compute the shortest distance along the road network between a cutting point (cp)
    and a fixed road starting point.

    Parameters
    ----------
    roads_gdf : GeoDataFrame
        GeoDataFrame of road geometries (LineString).
    cp : CuttingPoint
        Custom point class with attribute .geom (shapely Point).
    road_starting_point : Point
        Starting reference point on the road.

    Returns
    -------
    float
        Shortest path length along the road network between cp and road_starting_point.
    """
    try:
        # 1. Build graph from road geometries
        G = nx.Graph()
        for idx, road in roads_gdf.iterrows():
            geom = road.geometry
            if not isinstance(geom, LineString):
                continue
            coords = list(geom.coords)
            for i in range(len(coords) - 1):
                p1, p2 = coords[i], coords[i + 1]
                dist = Point(p1).distance(Point(p2))
                G.add_edge(p1, p2, weight=dist)

        if G.number_of_edges() == 0:
            logger.warning("Road graph is empty!")
            return float("inf")

        # 2. Snap cp and starting point to nearest road nodes
        def snap_to_graph(pt: Point):
            nearest_node = min(G.nodes, key=lambda n: Point(n).distance(pt))
            return nearest_node

        cp_node = snap_to_graph(cp.geom)
        start_node = snap_to_graph(road_starting_point)

        # 3. Compute shortest path length
        try:
            length = nx.shortest_path_length(
                G, source=cp_node, target=start_node, weight="weight"
            )
        except nx.NetworkXNoPath:
            logger.warning("No path found between cp and start_point in road network.")
            return float("inf")

        return length

    except Exception as e:
        logger.error("Error in dist_on_road(): %s", e)
        return float("inf")
