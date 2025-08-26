
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import Point

from difficulty_map.source.map_utils import TARGET_CRS


def generate_buffer_grid(segments, buffer_width, cell_size):
    """
    Generate a raster mask around given line segments, buffered by a given width.

    Parameters
    ----------
    segments : list of dict
        Each dict must have a 'geometry' key (LineString).
    buffer_width : float
        Buffer distance around the segments.
    cell_size : float
        Resolution of the raster grid.

    Returns
    -------
    mask : np.ndarray
        Binary raster mask (1 inside buffer, 0 outside).
    transform : affine.Affine
        Raster transform mapping rows/cols to coordinates.
    """
    union = gpd.GeoSeries([seg["geometry"] for seg in segments]).unary_union
    buffered = union.buffer(buffer_width)

    bounds = buffered.bounds
    width = int((bounds[2] - bounds[0]) // cell_size)
    height = int((bounds[3] - bounds[1]) // cell_size)

    transform = rasterio.transform.from_origin(bounds[0], bounds[3], cell_size, cell_size)

    mask = rasterize(
        [(buffered, 1)],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype="uint8",
    )

    return mask, transform


def analyze_cells(mask, transform, raster_altitude, segments):
    """
    Analyze raster cells inside the buffer to estimate difficulty.

    Parameters
    ----------
    mask : np.ndarray
        Binary raster mask (1 = inside buffer, 0 = outside).
    transform : affine.Affine
        Raster transform.
    raster_altitude : rasterio.DatasetReader
        Altitude raster source.
    segments : list of dict
        Each dict must have 'geometry' (LineString) and 'total_diff' (float).

    Returns
    -------
    GeoDataFrame
        With point geometries and difficulty values.
    """
    results = []

    for row, col in zip(*mask.nonzero()):
        x, y = rasterio.transform.xy(transform, row, col, offset="center")
        point = Point(x, y)

        alt = raster_altitude.read(1, window=rasterio.windows.Window(col, row, 1, 1))[0, 0]

        distances = [(s, s["geometry"].distance(point)) for s in segments]
        nearest_seg, dist_to_seg = min(distances, key=lambda x: x[1])
        #TODO : adapter avec les poids
        local_difficulty = alt * dist_to_seg * 0.8 + nearest_seg["total_diff"] * 0.2
        results.append({"geometry": point, "difficulty": local_difficulty})

    return gpd.GeoDataFrame(results, crs=TARGET_CRS)
