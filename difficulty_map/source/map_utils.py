import logging
from pathlib import Path
from collections import defaultdict

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.plot import plotting_extent
from rasterio.mask import mask
from shapely.geometry import LineString, MultiLineString

from difficulty_map.source.classes import Trail

# ----------------------------- #
# Global config
# ----------------------------- #

# Default country setting (can be switched to "fr")
COUNTRY = "it"

# ----------------------------- #
# PATH SETUP
# ----------------------------- #

# Automatically locate the 'data' folder relative to this script
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent  # Go up one level from 'core/'

if COUNTRY == "it":
    DATA_DIR = PROJECT_ROOT / "data" / "italia_test"
    TRAILS_PATH = DATA_DIR / "trails.shp"
    ROADS_PATH = DATA_DIR / "roads.shp"
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

logger = logging.getLogger(__name__)

def read_and_prepare_layers(original_crs=ORIGINAL_CRS, target_crs=TARGET_CRS):
    """
    Load and reproject trail and road vector layers.

    Parameters
    ----------
        original_crs: str 
            The CRS of the raw shapefiles.
        target_crs: str
            The target CRS for analysis.

    Returns
    -------
        tuple: (GeoDataFrame, GeoDataFrame) 
            Representing trails and roads.
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


def show_landform_utils(study_area):
    """
    Crop the slope raster to the study area and prepare data for plotting.

    Parameters
    ----------
        study_area: GeoDataFrame
        Polygon geometry defining the study area.

    Returns
    -------
        tuple:
            - np.ndarray: Cropped raster data with NaNs for nodata values.
            - list: [xmin, xmax, ymin, ymax] extent for plotting.
    """
    bbox_geojson = [study_area.geometry.iloc[0].__geo_interface__]
    with rasterio.open(RASTER_PATH) as src:
        out_image, out_transform = rio_mask(src, bbox_geojson, crop=True)
        data = out_image[0].astype("float32")
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
        xmin, xmax, ymin, ymax = plotting_extent(data, out_transform)
        extent = [xmin, xmax, ymin, ymax]
        logging.info("Slope raster prepared with shape %s", data.shape)
        return data, extent


def clip_layers(layers, study_area):
    """
    Clip one or more GeoDataFrames to a study area.

    Parameters
    ----------
        layers: list
            List of GeoDataFrames.
        study_area: GeoDataFrame
            Polygon geometry to clip to.

    Returns
    -------
        list: 
            List of clipped GeoDataFrames.
    """
    return [gpd.clip(layer, study_area) for layer in layers]


def mask_raster(bbox, src):
    """
    Mask a raster using a bounding box polygon.

    Parameters
    ----------
        bbox: shapely.geometry.Polygon
            Bounding box polygon.
        src: rasterio.io.DatasetReader
            Open raster dataset.

    Returns
    -------
        tuple:
            - np.ndarray: Masked raster data (nodata replaced with NaN).
            - dict: Updated raster metadata.
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

    Parameters
    ----------
        gdf: GeoDataFrame
            Input GeoDataFrame.

    Returns
    -------
        GeoDataFrame: 
            Copy of input with 'id' column added.
    """
    gdf = gdf.copy()
    gdf["id"] = gdf.index
    return gdf


def decompose_multilines(gdf):
    """
    Convert MultiLineStrings into individual LineStrings.

    Each segment is assigned a unique ID.

    Parameters
    ----------
        gdf: GeoDataFrame
            Input GeoDataFrame with LineString or MultiLineString geometries.

    Returns
    -------
        GeoDataFrame: 
            New GeoDataFrame with only LineString geometries.
    """
    decomposed = []
    for _, row in gdf.iterrows():
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
    """
    Create a dictionary mapping Trail objects to empty lists.

    Parameters
    ----------
        trails_gdf: GeoDataFrame
            GeoDataFrame containing trail geometries.

    Returns
    -------
        defaultdict: 
            Mapping {Trail: []}.
    """
    dico_trails = defaultdict(list)
    for _, row in trails_gdf.iterrows():
        trail = Trail(id=row["id"], geom=row["geometry"])
        dico_trails[trail] = []
    return dico_trails


def generate_initial_points(bounds, num_points=3):
    """
    Generate random points inside a bounding box.

    Parameters
    ----------
        bounds: tuple
            (xmin, ymin, xmax, ymax).
        num_points (int, optional): Number of points to generate. Defaults to 3.

    Returns
    -------
        pd.DataFrame: 
            DataFrame with columns [Name, X, Y].
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
