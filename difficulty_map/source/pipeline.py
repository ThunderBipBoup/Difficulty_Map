import logging
import os

import geopandas as gpd
import rasterio
from shapely.geometry import LineString, Point, box

from difficulty_map.source.buffer import generate_buffer_grid, analyze_cells
from difficulty_map.source.cutting_points import build_cutting_points
from difficulty_map.source.dijkstra import dijkstra
from difficulty_map.source.map_utils import (
    RASTER_PATH,
    TARGET_CRS,
    add_id_column,
    decompose_multilines,
    create_trails_dict,
    clip_layers,
)


def run_difficulty_analysis(
    trails: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    small_box,
    start_pt: Point,
    process_buffer: bool,
    buffer_width: float,
    cell_size: float,
    trails_threshold: float,
    roads_threshold: float,
    w_diff_on_tr: float,
    w_diff_off_tr: float,
):
    """
    Run the main difficulty analysis workflow from trails, roads, and raster data.

    Parameters
    ----------
    trails : gpd.GeoDataFrame
        Trails network.
    roads : gpd.GeoDataFrame
        Roads network.
    small_box : shapely.geometry.Polygon
        Study area bounding polygon.
    start_pt : shapely.geometry.Point
        Starting point of the analysis.
    process_buffer : bool
        If True, run buffer grid analysis.
    buffer_width : float
        Width of the buffer around segments for grid analysis.
    cell_size : float
        Raster cell resolution for buffer analysis.
    trails_threshold : float
        Maximum distance threshold to generate trail cutting points.
    roads_threshold : float
        Maximum distance between a trail and a road to consider them connected.
    w_diff_on_tr : float
        Weight of on-trail difficulty in final difficulty score.
    w_diff_off_tr : float
        Weight of off-trail difficulty in final difficulty score.

    Returns
    -------
    tuple
        (segments, trails_clip, roads_clip, gdf_cells, status)
        - segments : list of dict
            List of trail segments with difficulty metrics.
        - trails_clip : gpd.GeoDataFrame
            Clipped and processed trails.
        - roads_clip : gpd.GeoDataFrame
            Clipped and processed roads.
        - gdf_cells : gpd.GeoDataFrame or None
            Buffer grid cells with difficulty values (if enabled).
        - status : str
            Execution status ("OK" or error code).
    """
    with rasterio.open(RASTER_PATH) as src:
        logging.info("Raster loaded: %s", RASTER_PATH)
        logging.info("CRS: %s, Bounds: %s, Shape: %s", src.crs, src.bounds, src.shape)

        # Clip roads and trails to the study area
        study_area = gpd.GeoDataFrame(geometry=[small_box], crs=TARGET_CRS)
        roads_clip, trails_clip = [
            gpd.clip(layer, study_area) for layer in [roads, trails]
        ]

        # Add IDs and decompose multilines
        trails_clip = add_id_column(trails_clip)
        trails_clip_decomposed = decompose_multilines(trails_clip)
        trails_dict = create_trails_dict(trails_clip_decomposed)
        roads_clip = add_id_column(roads_clip)

        # Ensure study area intersects raster
        raster_extent = box(*src.bounds)
        if not study_area.intersects(raster_extent).any():
            logging.warning(
                "Study area is outside the raster extent, analysis aborted."
            )
            return None, None, None, None, "STUDY_AREA_OUTSIDE_RASTER"

        # Build cutting points between trails and roads
        all_cutting_points = build_cutting_points(
            trails_dict, roads, trails_threshold, roads_threshold
        )

        # Propagate difficulty using Dijkstra algorithm
        starting_points = [cp for cp in all_cutting_points if cp.is_connection_to_road]
        segments, metrics = dijkstra(starting_points, src, roads, start_pt)

        os.makedirs("export", exist_ok=True)
        gdf_result = gpd.GeoDataFrame(segments, geometry="geometry", crs=TARGET_CRS)
        gdf_result.to_file("export/trails_difficulty.shp")
        gdf_result.to_file(
            "export/trails_difficulty.gpkg", layer="segments", driver="GPKG"
        )

        # Optional buffer analysis
        gdf_cells = None
        if process_buffer:
            mask_arr, transform = generate_buffer_grid(
                segments, buffer_width, cell_size
            )
            gdf_buffer = analyze_cells(
                mask_arr, transform, src, segments, w_diff_on_tr, w_diff_off_tr
            )
            gdf_buffer = gdf_buffer[gdf_buffer.geometry.intersects(raster_extent)]
            gdf_cells = gdf_buffer[gdf_buffer["difficulty"] > 0]
            gdf_cells.to_file("export/buffer_cells.shp")
            gdf_cells.to_file("export/buffer_cells.gpkg", layer="buffer", driver="GPKG")

        logging.info("Performance summary: %s", metrics)

    return segments, trails_clip, roads_clip, gdf_cells, "OK"


def compute_alt_out_trail(point, segment, src):
    """
    Compute altitude difference between a point and its projection on a trail segment.

    Parameters
    ----------
    point : shapely.geometry.Point
        The original point.
    segment : shapely.geometry.LineString
        Trail segment to project onto.
    src : rasterio.io.DatasetReader
        Open raster dataset.

    Returns
    -------
    float or None
        Altitude difference (point - projection), or None if no valid data.
    """
    projected_point = segment.interpolate(segment.project(point))
    val_original = list(src.sample([(point.x, point.y)]))[0][0]
    val_projected = list(src.sample([(projected_point.x, projected_point.y)]))[0][0]
    if val_original == -9999 or val_projected == -9999:
        return None
    return val_original - val_projected


def analyze_study_points(study_points, segments, w_diff_on_tr, w_diff_off_tr):
    """
    Analyze study points against trail difficulty metrics.

    Parameters
    ----------
    study_points : list of shapely.geometry.Point or list of tuple
        Points to analyze (X, Y or Point).
    segments : list of dict
        Trail segments with difficulty metrics.
    w_diff_on_tr : float
        Weight of on-trail difficulty.
    w_diff_off_tr : float
        Weight of off-trail difficulty.

    Returns
    -------
    gpd.GeoDataFrame
        Points with local difficulty metrics.
    """
    with rasterio.open(RASTER_PATH) as src:
        results = []
        for pt in study_points:
            if isinstance(pt, tuple):
                pt = Point(pt)

            # Find nearest trail segment
            nearest_seg = min(segments, key=lambda s: s["geometry"].distance(pt))
            dist_to_seg = float(nearest_seg["geometry"].distance(pt))

            # Compute altitude difference to projected point
            diff_alt_w_trail = (
                compute_alt_out_trail(pt, nearest_seg["geometry"], src) or 0
            )

            # Weighted difficulty
            diff = dist_to_seg * diff_alt_w_trail * float(w_diff_on_tr) + nearest_seg[
                "total_diff"
            ] * float(w_diff_off_tr)

            results.append(
                {
                    "geometry": pt,
                    "dist_on_trails": nearest_seg["total_dist"],
                    "total_elev_gain": nearest_seg["total_elev_gain"],
                    "total_descent": nearest_seg["total_descent"],
                    "dist_out_trail": dist_to_seg,
                    "diff_alt_w_trail": diff_alt_w_trail,
                    "dist_road": nearest_seg["dist_road"],
                    "diff": diff,
                }
            )

    return gpd.GeoDataFrame(results, crs=TARGET_CRS)


def project_point_on_nearest_road(
    roads_gdf: gpd.GeoDataFrame, user_point: Point
) -> Point:
    """
    Project a point onto the nearest road geometry in a GeoDataFrame.

    Parameters
    ----------
    roads_gdf : gpd.GeoDataFrame
        Roads layer.
    user_point : shapely.geometry.Point
        Point to project.

    Returns
    -------
    shapely.geometry.Point
        Projected point on the nearest road, or original point if no valid road.
    """
    if roads_gdf.empty:
        return user_point

    closest_idx = roads_gdf.geometry.distance(user_point).idxmin()
    closest_geom = roads_gdf.loc[closest_idx].geometry

    if not isinstance(closest_geom, LineString):
        return user_point

    return closest_geom.interpolate(closest_geom.project(user_point))
