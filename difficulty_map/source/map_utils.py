import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from rasterio.mask import mask
from shapely.geometry import LineString, MultiLineString

from .classes import *

# ----------------------------
# Global config
# ----------------------------
COUNTRY = "it"

logger = logging.getLogger(__name__)
# ----------------------------- #
# PATH SETUP
# ----------------------------- #


# Automatically locate the 'data' folder relative to this script
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent  # Go up one level from 'core/'

if COUNTRY == "it":
    DATA_DIR = PROJECT_ROOT / "data" / "italia_test"
    TRAILS_PATH = DATA_DIR / "SENTIERI.shp"
    ROADS_PATH = DATA_DIR / "Viabilita_Pubblica.shp"
    RASTER_PATH = DATA_DIR / "slope_cropped_area.tif"
    ORIGINAL_CRS = "EPSG:3004"
    TARGET_CRS = "EPSG:32632"

elif COUNTRY == "fr":
    DATA_DIR = PROJECT_ROOT / "data" / "france_test"
    TRAILS_PATH = DATA_DIR / "roads_src_adjusted.shp"
    ROADS_PATH = DATA_DIR / "railways_src_adjusted.shp"
    RASTER_PATH = DATA_DIR / "slope_fr.tif"
    ORIGINAL_CRS = "EPSG:2154"
    TARGET_CRS = "EPSG:2154"

# ----------------------------- #
# DATA LOADING AND PREPARATION
# ----------------------------- #


def read_and_prepare_layers(original_crs=ORIGINAL_CRS, target_crs=TARGET_CRS):
    """
    Load trails and roads shapefiles, assign and reproject CRS.
    """
    logging.info("Reading and preparing vector layers")
    trails = (
        gpd.read_file(TRAILS_PATH)
        .set_crs(original_crs, allow_override=True)
        .to_crs(target_crs)
    )
    roads = (
        gpd.read_file(ROADS_PATH)
        .set_crs(original_crs, allow_override=True)
        .to_crs(target_crs)
    )
    return trails, roads


def clip_layers(layers, study_area):
    """
    Clip one or more GeoDataFrames to a study area.
    """
    return [gpd.clip(layer, study_area) for layer in layers]



def mask_raster(bbox, src):
    """
    Apply a bounding box mask to a raster and return the masked array and updated metadata.
    """
    out_image, out_transform = mask(src, [bbox.__geo_interface__], crop=True)
    out_meta = src.meta.copy()
    out_meta.update(
        {
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
        }
    )
    data = out_image[0]
    data = np.where(data == -9999.0, np.nan, data)
    return data, out_meta


# ----------------------------- #
# TRAIL GEOMETRY PROCESSING
# ----------------------------- #


def add_id_column(gdf):
    """
    Add a unique 'id' column to a GeoDataFrame.
    """
    gdf = gdf.copy()
    gdf["id"] = gdf.index
    return gdf


def decompose_multilines(gdf):
    """
    Split MultiLineStrings into individual LineStrings, assigning unique IDs.
    """
    decomposed = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        if isinstance(geom, MultiLineString):
            for i, line in enumerate(geom.geoms):
                if isinstance(line, LineString) and not line.is_empty:
                    new_row = row.copy()
                    new_row["geometry"] = line
                    new_row["id"] = f"{row['id']}_{i}"
                    decomposed.append(new_row)
        elif isinstance(geom, LineString):
            new_row = row.copy()
            new_row["geometry"] = geom
            decomposed.append(new_row)
    return gpd.GeoDataFrame(decomposed, crs=gdf.crs)


def create_trails_dict(trails_gdf):
    dico_trails = defaultdict(list)
    for _, row in trails_gdf.iterrows():
        trail = Trail(id=row["id"], geom=row["geometry"])
        dico_trails[trail] = []
    return dico_trails


def generate_initial_points(bounds, num_points=3):
    """
    Génère un DataFrame de points aléatoires dans la zone définie par bounds.

    Args:
        bounds (tuple): (xmin, ymin, xmax, ymax)
        num_points (int): nombre de points à générer

    Returns:
        pd.DataFrame: colonnes X, Y, Name
    """
    xmin, ymin, xmax, ymax = bounds
    xs = np.random.uniform(xmin, xmax, num_points)
    ys = np.random.uniform(ymin, ymax, num_points)
    return pd.DataFrame(
        [
            {"Name": f"Point {i+1}", "X": x, "Y": y}
            for i, (x, y) in enumerate(zip(xs, ys))
        ]
    )
