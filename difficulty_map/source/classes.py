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

    def __init__(self, geom, roads, roads_threshold):
        self.geom = geom
        self.dict_neighbors = defaultdict(list)
        self.dist_on_roads = float("inf")
        self.best_diff = float("inf")
        self.total_dist = float("inf")
        self.total_elev_gain = float("inf")
        self.total_descent = float("inf")
        self.is_connection_to_road = roads.distance(self.geom).min() < roads_threshold
    def __hash__(self):
        return hash((self.geom.x, self.geom.y))

    def __eq__(self, other):
        return self.geom.equals(other.geom)

    def __lt__(self, other):
        return self.best_diff < other.best_diff


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
