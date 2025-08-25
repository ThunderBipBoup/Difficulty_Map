from shapely.geometry import Point
from .classes import Graph, Trail
import logging

def build_graph_from_trails(trails_dict, raster_src=None):
    """
    Constructs a graph of CuttingPoints and Trails from input geometries.

    Parameters
    ----------
    trails_dict : dict
        Dictionary mapping trails to a list of CuttingPoint instances along the trail.
    raster_src : rasterio.io.DatasetReader, optional
        Raster data source (not used in this function, but passed for consistency).

    Returns
    -------
    graph : Graph
        The resulting trail connectivity graph.
    all_cutting_points : list
        List of all CuttingPoint instances used in the graph.
    """

    graph = Graph()
    all_cutting_points = []

    logging.info("Building intra-trail edges")
    for trail in trails_dict.keys():
        cps = trails_dict[trail]
        assert isinstance(cps, list), f"Expected a list of CuttingPoints for trail {trail.id}"
        all_cutting_points.extend(cps)

        for i in range(len(cps) - 1):
            cp1, cp2 = cps[i], cps[i + 1]

            # Add edge between consecutive CuttingPoints
            graph.add_edge(cp1, cp2)

            # Store Trail info in neighbors dict
            cp1.dict_neighbors[cp2].append(trail)
            cp2.dict_neighbors[cp1].append(trail)

    logging.info("Adding inter-trail connections...")
    unique_cpoints = set(all_cutting_points)
    for cp in unique_cpoints:
        add_intertrail_connections(graph, cp)

    logging.debug("Graph built with {len(graph.nodes)} nodes and {len(graph.edges)} edges.")
    return graph, all_cutting_points


def add_intertrail_connections(graph, cp):
    """
    Adds edges between a CuttingPoint and its cross-trail neighbors.

    Parameters
    ----------
    graph : Graph
        The graph to update.
    cp : CuttingPoint
        A CuttingPoint potentially connected to other trails.
    """
    for neighbor in cp.dict_neighbors:
        if neighbor is not None:
            graph.add_edge(cp, neighbor)
