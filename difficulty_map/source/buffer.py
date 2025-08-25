


import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from shapely.geometry import Point, box

from .map_utils import *


def generate_buffer_grid(segments, buffer_width, cell_size):
    # Unir tous les segments en un seul MultiLineString
    union = gpd.GeoSeries([seg["geometry"] for seg in segments]).unary_union
    buffered = union.buffer(buffer_width)
    # Définir la grille raster
    bounds = buffered.bounds
    width = int((bounds[2] - bounds[0]) // cell_size)
    height = int((bounds[3] - bounds[1]) // cell_size)
    
    transform = rasterio.transform.from_origin(bounds[0], bounds[3], cell_size, cell_size)

    mask = rasterize(
        [(buffered, 1)],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        dtype='uint8'
    )

    return mask, transform

def analyze_cells(mask, transform, raster_altitude, segments):
    height, width = mask.shape
    results = []

    for row in range(height):
        for col in range(width):
            if mask[row, col] == 0:
                continue  # out of buffer

            x, y = rasterio.transform.xy(transform, row, col, offset='center')
            point = Point(x, y)

            # Local altitude
            window = rasterio.windows.Window(col, row, 1, 1)
            alt = raster_altitude.read(1, window=window)[0, 0]

            nearest_seg = min(segments, key=lambda s: s["geometry"].distance(point))
            dist_to_seg = nearest_seg["geometry"].distance(point)
            inherited_difficulty = nearest_seg["total_diff"]

            # TODO : adapter avec les poids
            local_difficulty = alt * dist_to_seg * 0.8 + inherited_difficulty *0.2
            results.append({
                "geometry": Point(x, y),
                "difficulty": local_difficulty
            })

    return gpd.GeoDataFrame(results, crs=TARGET_CRS)
