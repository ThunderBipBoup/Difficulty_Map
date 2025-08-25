from shapely.geometry import LineString
from collections import defaultdict
from shapely.geometry import Point


class CuttingPoint:
    """
    Cutting points are either intersections of trails, or end of trails.

    Attributes
    ----------
    geom : Shapely Point
        Geometry of the cutting point
    dict_neighbors : dict ([CuttingPoint] -> list)
        Each cutting point has a dictionnary with his neighbors cutting points
        as keys, and that return a list of trail that they are both on as a value
    dist_on_roads : float
        Distance driven on road from the starting point to the point where we
        leave road for walking on trails to reach the cutting point.
    best_diff : float
        It is the minimal difficulty that we calculate for now to reach this
        cutting point.
    total_dist : float
        It is the distance travelled on trails before reaching the cutting
        point, for this current best_diff.
    total_elev_gain :  float
        This is the sum of the ascents climbed to reach the cutting point.
    total_descent : float
        This is the sum of the downward slope to reach the cutting point.
    is_connection_to_road : bool
        True if the cutting point is connecting a trail to a road.

    """

    def __init__(self, geom, roads):
        self.geom = geom
        self.dict_neighbors = defaultdict(list)
        self.dist_on_roads = float("inf")
        self.best_diff = float("inf")
        self.total_dist = float("inf")
        self.total_elev_gain = float("inf")
        self.total_descent = float("inf")
        self.is_connection_to_road = roads.distance(self.geom).min() < 40

    # def __hash__(self):
    # return hash((self.geom.x, self.geom.y))

    # def __eq__(self, other):
    # return self.geom.equals(other.geom)

    def __lt__(self, other):
        return self.best_diff < other.best_diff


# TODO : si ça se trouve il y a pas besoin de la classe Graph


class Graph:
    def __init__(self):
        self.edges = defaultdict(dict)  # cp -> neighbors -> List[geometry,processed)]
        self.nodes = set()

    def add_edge(self, cp1, cp2):
        seg_geom_1 = LineString([cp1.geom, cp2.geom])
        self.edges[cp1][cp2] = [seg_geom_1, 0]
        seg_geom_2 = LineString([cp2.geom, cp1.geom])
        self.edges[cp2][cp1] = [seg_geom_2, 0]  # non-oriented
        self.nodes.add(cp1)
        self.nodes.add(cp2)

    def edge_processed(self, cp1, cp2):
        self.edges[cp1][cp2][1] += 1
        self.edges[cp2][cp1][1] += 1


class Trail:
    """
    Created from a GeoDataFrame file of trails.

    Attributes
    ----------
    id : int
        Unique identifier.
    geom : Shapely Point
        Geometry of the trail (Linestring)

    Methods
    -------
    endpoints()
        Returns the two ends (Points) of the trail
    """

    def __init__(self, id, geom):
        self.id = id
        self.geom = geom

    def endpoints(self):
        coords = list(self.geom.coords)
        return Point(coords[0]), Point(coords[-1])

    def __eq__(self, other):
        return isinstance(other, Trail) and self.id == other.id

    def __hash__(self):
        return hash(self.id)


from dataclasses import dataclass
from shapely.geometry import LineString
from typing import Any

@dataclass
class SegmentResult:
    """
    Represents the difficulty analysis for a segment of a trail between two cutting points.

    Attributes
    ----------
    geometry : LineString
        The geometry of the trail segment.
    segment_difficulty : float
        Difficulty score of the segment, which combines distance traveled
        and elevation changes (ascents increase difficulty, descents decrease it).
    total_difficulty : float
        Cumulative difficulty from the starting cutting point to the end of this segment.
    position_along_trail : float
        Position of this segment along the trail (used as a key for ordering).
    dist_on_roads : float
        Distance traveled on roads before entering the trails to reach this segment.
    trail_id : int
        Identifier of the trail this segment belongs to.
    start_cp : Any
        Starting cutting point object.
    end_cp : Any
        Ending cutting point object.
    segment_length : float
        Length of the segment in map units.
    total_dist : float
        Cumulative trail distance from start up to this segment.
    elevation_gain : float
        Elevation gain only for this segment.
    total_elev_gain : float
        Cumulative elevation gain up to this segment.
    descent : float
        Elevation loss only for this segment.
    total_descent : float
        Cumulative elevation loss up to this segment.
    """
    geometry: LineString
    segment_difficulty: float
    total_difficulty: float
    position_along_trail: float
    dist_on_roads: float
    trail_id: int
    start_cp: Any
    end_cp: Any
    segment_length: float
    total_dist: float
    elevation_gain: float
    total_elev_gain: float
    descent: float
    total_descent: float
