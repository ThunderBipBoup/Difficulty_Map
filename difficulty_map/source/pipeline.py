
import logging
import os

import geopandas as gpd
from rasterio.mask import mask
from rasterio.plot import plotting_extent
from shapely.geometry import LineString, Point

from .buffer import *
from .classes import *
from .cutting_points import *
from .dijkstra import *
from .graph import *
from .map_utils import *
from .plot_utils import *
from .roads import *


# la fonction inutile
def load_input_data():
    logging.info("Loading raster data")
    logging.info("Reading and preparing vector layers")
    trails, roads = read_and_prepare_layers()
    return trails, roads



def run_difficulty_analysis(trails, roads, small_box, start_pt, process_buffer, buffer_width, cell_size,threshold_btw_cp):
    src = rasterio.open(RASTER_PATH)
    print("Raster ouvert ✅")
    print("Chemin :", RASTER_PATH)
    print("CRS :", src.crs)
    print("Bounds :", src.bounds)
    print("Shape :", src.shape)
    print("Dtype :", src.dtypes)
    print("Nodata :", src.nodata)
    data = src.read(1)  # première bande
    print("Min:", np.nanmin(data))
    print("Max:", np.nanmax(data))
    print("Unique nodata :", np.unique(data[data == src.nodata])[:10])
    
    study_area = gpd.GeoDataFrame(geometry=[small_box],crs=TARGET_CRS)
    logging.info("Clipping trails and roads to study area")
    roads_clip, trails_clip = [gpd.clip(layer, study_area) for layer in [roads, trails]]
    

    logging.info("Adding unique IDs and decomposing geometries")
    trails_clip = add_id_column(trails_clip)
    trails_clip_decomposed = decompose_multilines(trails_clip)
    trails_dict = create_trails_dict(trails_clip_decomposed)

    roads_clip = add_id_column(roads_clip)
    logging.info("Ceation of a mask of the valid areas of the raster")    
    # On crée un masque des zones valides du raster
    bounds = src.bounds
    raster_extent = box(*bounds)

    # Vérifier si la zone intersecte le raster
    if not study_area.intersects(raster_extent).any():
        logging.warning("Study area is outside the raster extent, analysis aborted.")
        return None, None, None, None, None, "STUDY_AREA_OUTSIDE_RASTER"

    # -----------------------------
    # 1. Initialize Cutting Points
    # -----------------------------

    logging.info("Initializing CuttingPoints")
    filled_dict_trails = initialize_cutting_points(trails_dict, roads,threshold_btw_cp)

    # -----------------------------
    # 2. Build graph
    # -----------------------------

    logging.info("Building graph from trail network")
    graph, all_cutting_points = build_graph_from_trails(filled_dict_trails, src)

    # -----------------------------
    # 3. Launch propagation
    # -----------------------------

    logging.info("Starting propagation...")
    starting_points = [cp for cp in all_cutting_points if cp.is_connection_to_road]

    print(f" Number of nodes: {len(graph.nodes)}")
    print(f" Number of edges: {len(graph.edges)}")


    segments, visited_cps, metrics = dijkstra( starting_points, src,roads,start_pt)
            
    # -----------------------------
    # 4. Export results
    # -----------------------------
    # Ensure export directory exists
    os.makedirs("export", exist_ok=True)
    
    logging.info("Exporting results to shapefile")
    print("Type de segments:", type(segments))
    if isinstance(segments, list):
        print("Longueur:", len(segments))
        if len(segments) > 0:
            print("Premier élément:", segments[0])

    gdf_result = gpd.GeoDataFrame(segments, geometry="geometry", crs=TARGET_CRS)
    gdf_result.to_file("export/trails_difficulty.shp")# Export to Shapefile (QGIS-compatible)

    #  Also export as GeoPackage
    gdf_result.to_file("export/trails_difficulty.gpkg", layer="segments", driver="GPKG")

    # -----------------------------
    # 5. Buffer
    # -----------------------------

    if process_buffer:
        mask, transform= generate_buffer_grid(segments,buffer_width, cell_size)
        gdf_buffer=analyze_cells(mask, transform, src, segments)

        # On garde uniquement les cellules dans le raster
        gdf_buffer = gdf_buffer[gdf_buffer.geometry.intersects(raster_extent)]
        gdf_cells=gdf_buffer[(gdf_buffer["difficulty"]>0)]

        # Export buffer cells to Shapefile and GeoPackage
        gdf_cells.to_file("export/buffer_cells.shp")
        gdf_cells.to_file("export/buffer_cells.gpkg", layer="buffer", driver="GPKG")
    else:
        gdf_cells=None
    # -----------------------------
    # 6. Performance
    # -----------------------------

    logging.info("Plotting difficulty map")

    print("\n Performance Summary")
    for key, value in metrics.items():
        print(f"{key.replace('_', ' ').capitalize()}: {value}")

    return segments, trails_clip, roads_clip, gdf_cells, "OK"



def study_area_displaying(trails, roads, study_area, show_landform):
    logging.info("Clipping trails and roads to study area")
    roads_clip, trails_clip = clip_layers([roads, trails], study_area)
    data, extent = None, None

    if show_landform:
        bbox_geojson = [study_area.geometry.iloc[0].__geo_interface__]
        with rasterio.open(RASTER_PATH) as src:
            logging.info(f"Raster opened: crs={src.crs} bounds={src.bounds}")
            out_image, out_transform = mask(src, bbox_geojson, crop=True)

            # 1 bande
            data = out_image[0].astype("float32")

            # nodata → NaN (si pas défini, on ne touche à rien)
            if src.nodata is not None:
                data[data == src.nodata] = np.nan

            # extent robuste = (xmin, xmax, ymin, ymax)
            xmin, xmax, ymin, ymax = plotting_extent(data, out_transform)
            extent = [xmin, xmax, ymin, ymax]

            logging.info(
                f"Slope raster prepared: shape={data.shape} "
                f"stats=({np.nanmin(data):.2f}, {np.nanmax(data):.2f}) "
                f"extent={extent} "
                f"study_area_bounds={tuple(study_area.total_bounds)}"
            )

    return roads_clip, trails_clip, (data, extent)



def compute_alt_out_trail(point, segment, src):
    """
    Calcule la différence d'altitude entre le point et son point projeté sur un segment.
    
    Args:
        point (shapely.geometry.Point): Le point d'étude à analyser.
        segment (shapely.geometry.LineString): Le segment de sentier.
        src (rasterio.io.DatasetReader): La source raster d'altitude.

    Returns:
        float: alt_out_trail (positive si le point est plus haut que le sentier)
    """
    # Projeter le point sur le segment
    projected_dist = segment.project(point)
    projected_point = segment.interpolate(projected_dist)

    # Extraire les altitudes
    coords_original = [(point.x, point.y)]
    coords_projected = [(projected_point.x, projected_point.y)]

    val_original = list(src.sample(coords_original))[0][0]
    val_projected = list(src.sample(coords_projected))[0][0]

    # Gérer les valeurs no-data
    if val_original == -9999 or val_projected == -9999:
        return None  # ou np.nan, ou 0, selon ton usage

    alt_out_trail = val_original - val_projected
    return alt_out_trail


def analyze_study_points(study_points, segments, w_diff_on_tr, w_diff_off_tr):
    src = rasterio.open(RASTER_PATH)
    transform = src.transform  # <-- ici on récupère la transform

    results = []

    for pt in study_points:
        # pt est un shapely Point ou un tuple (x, y)
        if isinstance(pt, tuple):
            pt = Point(pt)
        
        # Convertir coordonnées en indices raster
        row, col = ~transform * (pt.x, pt.y)
        row, col = int(row), int(col)

        try:
            # Lecture de l'altitude depuis le raster
            window = rasterio.windows.Window(col, row, 1, 1)
            alt = src.read(1, window=window)[0, 0]
        except:
            alt = np.nan  # en cas de sortie du raster ou problème

        # Trouver segment le plus proche
        nearest_seg = min(segments, key=lambda s: s["geometry"].distance(pt))
        dist_to_seg = nearest_seg["geometry"].distance(pt)
        dist_to_seg =float()
        diff_alt_w_trail = compute_alt_out_trail(pt, nearest_seg["geometry"], src)
        if diff_alt_w_trail is None:
            diff_alt_w_trail = 0
        print("diff_alt_w_trail :", diff_alt_w_trail)
        print("dist_to_seg :", dist_to_seg)
        w_diff_on_tr = np.array(w_diff_on_tr, dtype=float)
        w_diff_off_tr = np.array(w_diff_off_tr, dtype=float)
        diff = dist_to_seg * diff_alt_w_trail * w_diff_on_tr + nearest_seg["total_diff"] * w_diff_off_tr
        results.append({
            "geometry": pt,
            "dist_on_trails":nearest_seg["total_dist"],
            "total_elev_gain":nearest_seg["total_elev_gain"],
            "total_descent":nearest_seg["total_descent"],
            "dist_out_trail":dist_to_seg,
            "diff_alt_w_trail": diff_alt_w_trail,
            "dist_road": nearest_seg["dist_road"],
            "diff" : diff
        })
    return gpd.GeoDataFrame(results, crs=TARGET_CRS)





def project_point_on_nearest_road(roads_gdf: gpd.GeoDataFrame, user_point: Point) -> Point:
    """
    Project a point onto the nearest road in a GeoDataFrame.

    Parameters:
        roads_gdf (GeoDataFrame): GeoDataFrame containing LineString roads.
        user_point (Point): The point to be projected.

    Returns:
        Point: The point projected onto the closest road.
    """
    if roads_gdf.empty:
        return user_point  # fallback

    # Find index of closest road
    distances = roads_gdf.geometry.distance(user_point)
    closest_idx = distances.idxmin()
    closest_geom = roads_gdf.loc[closest_idx].geometry

    if not isinstance(closest_geom, LineString):
        return user_point  # fallback

    # Project point onto the closest road line
    projected_point = closest_geom.interpolate(closest_geom.project(user_point))
    return projected_point
