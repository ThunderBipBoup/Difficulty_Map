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


# -----------------------------------------------------------------------------
# 1. Pipeline principal
# -----------------------------------------------------------------------------

def run_difficulty_analysis(
    trails: gpd.GeoDataFrame,
    roads: gpd.GeoDataFrame,
    small_box,
    start_pt: Point,
    process_buffer: bool,
    buffer_width: float,
    cell_size: float,
    threshold_btw_cp: float,
):
    """
    Lance l'analyse de difficulté à partir des chemins et routes.

    Args:
        trails: GeoDataFrame des sentiers.
        roads: GeoDataFrame des routes.
        small_box: Zone d'étude (shapely Polygon).
        start_pt: Point de départ.
        process_buffer: Active l'analyse en grille tampon si True.
        buffer_width: Largeur du buffer.
        cell_size: Taille de cellule du raster.
        threshold_btw_cp: Distance seuil pour points de coupure.

    Returns:
        tuple: (segments, trails_clip, roads_clip, gdf_cells, status)
    """
    with rasterio.open(RASTER_PATH) as src:
        logging.info("Raster loaded: %s", RASTER_PATH)
        logging.info("CRS: %s, Bounds: %s, Shape: %s", src.crs, src.bounds, src.shape)

        study_area = gpd.GeoDataFrame(geometry=[small_box], crs=TARGET_CRS)
        roads_clip, trails_clip = [gpd.clip(layer, study_area) for layer in [roads, trails]]

        trails_clip = add_id_column(trails_clip)
        trails_clip_decomposed = decompose_multilines(trails_clip)
        trails_dict = create_trails_dict(trails_clip_decomposed)

        roads_clip = add_id_column(roads_clip)

        # Vérification intersection raster
        raster_extent = box(*src.bounds)
        if not study_area.intersects(raster_extent).any():
            logging.warning("Study area is outside the raster extent, analysis aborted.")
            return None, None, None, None, "STUDY_AREA_OUTSIDE_RASTER"

        # Points de coupure
        all_cutting_points = build_cutting_points(trails_dict, roads, threshold_btw_cp)

        # Propagation
        starting_points = [cp for cp in all_cutting_points if cp.is_connection_to_road]
        segments, metrics = dijkstra(starting_points, src, roads, start_pt)

        # Export résultats
        os.makedirs("export", exist_ok=True)
        gdf_result = gpd.GeoDataFrame(segments, geometry="geometry", crs=TARGET_CRS)
        gdf_result.to_file("export/trails_difficulty.shp")
        gdf_result.to_file("export/trails_difficulty.gpkg", layer="segments", driver="GPKG")

        # Buffer cells
        gdf_cells = None
        if process_buffer:
            mask_arr, transform = generate_buffer_grid(segments, buffer_width, cell_size)
            gdf_buffer = analyze_cells(mask_arr, transform, src, segments)
            gdf_buffer = gdf_buffer[gdf_buffer.geometry.intersects(raster_extent)]
            gdf_cells = gdf_buffer[gdf_buffer["difficulty"] > 0]
            gdf_cells.to_file("export/buffer_cells.shp")
            gdf_cells.to_file("export/buffer_cells.gpkg", layer="buffer", driver="GPKG")

        # Performance
        logging.info("Performance summary: %s", metrics)

    return segments, trails_clip, roads_clip, gdf_cells, "OK"


# -----------------------------------------------------------------------------
# 2. Affichage de l'aire d'étude avec raster
# -----------------------------------------------------------------------------




# -----------------------------------------------------------------------------
# 3. Analyse altimétrique locale
# -----------------------------------------------------------------------------

def compute_alt_out_trail(point, segment, src):
    """
    Calcule la différence d'altitude entre un point et sa projection sur un segment.
    """
    projected_point = segment.interpolate(segment.project(point))
    val_original = list(src.sample([(point.x, point.y)]))[0][0]
    val_projected = list(src.sample([(projected_point.x, projected_point.y)]))[0][0]
    if val_original == -9999 or val_projected == -9999:
        return None
    return val_original - val_projected


def analyze_study_points(study_points, segments, w_diff_on_tr, w_diff_off_tr):
    """Analyse des points d'étude et calcul des difficultés locales."""
    with rasterio.open(RASTER_PATH) as src:
        results = []
        for pt in study_points:
            if isinstance(pt, tuple):
                pt = Point(pt)

            nearest_seg = min(segments, key=lambda s: s["geometry"].distance(pt))
            dist_to_seg = float(nearest_seg["geometry"].distance(pt))
            diff_alt_w_trail = compute_alt_out_trail(pt, nearest_seg["geometry"], src) or 0

            diff = (
                dist_to_seg * diff_alt_w_trail * float(w_diff_on_tr)
                + nearest_seg["total_diff"] * float(w_diff_off_tr)
            )

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


# -----------------------------------------------------------------------------
# 4. Projection de points sur la route la plus proche
# -----------------------------------------------------------------------------

def project_point_on_nearest_road(roads_gdf: gpd.GeoDataFrame, user_point: Point) -> Point:
    """
    Projette un point sur la route la plus proche contenue dans le GeoDataFrame.
    """
    if roads_gdf.empty:
        return user_point

    closest_idx = roads_gdf.geometry.distance(user_point).idxmin()
    closest_geom = roads_gdf.loc[closest_idx].geometry

    if not isinstance(closest_geom, LineString):
        return user_point

    return closest_geom.interpolate(closest_geom.project(user_point))
