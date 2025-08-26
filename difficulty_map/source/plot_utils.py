import logging
from typing import Optional, Tuple, List

import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib import cm
from shapely.geometry import LineString, Point
from mpl_toolkits.axes_grid1 import make_axes_locatable

from difficulty_map.source import map_utils


# ----------------------------- #
# BASIC UTILITIES
# ----------------------------- #
def _init_plot(figsize=(8, 8), title: str = "") -> Tuple[plt.Figure, plt.Axes]:
    """Initialize a matplotlib figure and axes with optional title and labels."""
    fig, ax = plt.subplots(figsize=figsize)
    if title:
        ax.set_title(title)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    return fig, ax


def _plot_roads_and_trails(ax, roads_clip: Optional[gpd.GeoDataFrame], trails_clip: gpd.GeoDataFrame, 
                           alpha_tr=1):
    """Plot roads and trails on the map."""
    if trails_clip is not None:
        trails_clip.plot(ax=ax, color="black", linewidth=1, alpha=alpha_tr, zorder=8, label="Trails")
    if roads_clip is not None:
        roads_clip.plot(ax=ax, color="pink", linewidth=3, zorder=9, label="Public Roads")


def _plot_confirmed_points(ax, confirmed_points: gpd.GeoDataFrame):
    """Plot confirmed points with labels."""
    if confirmed_points is None or confirmed_points.empty:
        return
    gdf_points = gpd.GeoDataFrame(
        confirmed_points,
        geometry=gpd.points_from_xy(confirmed_points["X"], confirmed_points["Y"]),
        crs=map_utils.TARGET_CRS,
    )
    gdf_points.plot(ax=ax, color="blue", marker="o", markersize=50, zorder=5)

    for _, row in gdf_points.iterrows():
        ax.text(
            row.geometry.x + 50,
            row.geometry.y + 50,
            str(row["Name"]),
            fontsize=9,
            color="blue",
            zorder=6,
            bbox={"facecolor": "ivory", "alpha": 0.8, "edgecolor": "none", "boxstyle": "round,pad=0.2"},
        )


def _plot_slope(ax, fig, slope_result, cmap="terrain", label="Slope (units)",alpha=1):
    """Plot a slope raster with colorbar."""
    slope_data, slope_extent = slope_result
    if slope_data is None or slope_extent is None or np.isnan(slope_data).all():
        logging.warning("Slope data missing or invalid.")
        return

    im = ax.imshow(
        slope_data,
        cmap=cmap,
        extent=slope_extent,
        origin="upper",
        zorder=1,
        alpha=alpha
    )
    ax.set_xlim(slope_extent[0], slope_extent[1])
    ax.set_ylim(slope_extent[2], slope_extent[3])

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("bottom", size="5%", pad=0.4)
    cb = fig.colorbar(im, cax=cax, orientation="horizontal")
    cb.set_label(label)


def _plot_segments(ax, segments: List[dict], cmap_name="rainbow") -> Tuple[mcolors.Normalize, cm.ScalarMappable]:
    """Plot trail segments colored by difficulty."""
    difficulties = [seg["total_diff"] for seg in segments if "total_diff" in seg]
    if not difficulties:
        logging.error("No difficulties found in the segments.")
        return None, None

    vmin, vmax = min(difficulties), max(difficulties)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.get_cmap(cmap_name)

    for seg in segments:
        line: LineString = seg["geometry"]
        diff = seg["total_diff"]
        color = cmap(norm(diff))
        if isinstance(line, LineString):
            x, y = line.xy
            ax.plot(x, y, color=color, linewidth=2, alpha=0.9, zorder=10)
        else:
            logging.warning("Segment geometry is not a LineString: %s", type(line))

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    return norm, sm


def _plot_cells(ax, gdf_cells: gpd.GeoDataFrame):
    """Plot background cells with difficulty values."""
    if gdf_cells is None or "difficulty" not in gdf_cells.columns:
        return
    vmin = gdf_cells["difficulty"].quantile(0.05)
    vmax = gdf_cells["difficulty"].quantile(0.95)
    gdf_cells.plot(
        ax=ax,
        column="difficulty",
        cmap="rainbow",
        markersize=40,
        alpha=0.8,
        vmin=vmin,
        vmax=vmax,
    )


def _plot_study_points(ax, gdf_study_points: gpd.GeoDataFrame):
    """Plot study points colored by their difficulty values."""
    if gdf_study_points is None or gdf_study_points.empty:
        return
    if "diff" not in gdf_study_points.columns:
        logging.warning("Column 'diff' is missing in gdf_study_points.")
        return

    gdf_study_points.plot(
        ax=ax,
        column="diff",
        cmap="rainbow",
        markersize=80,
        label="Distance driven on road",
        marker="o",
        linewidth=0.5,
        zorder=7,
    )


# ----------------------------- #
# MAIN PLOTTING FUNCTIONS
# ----------------------------- #

def plot_study_area(
    roads_clip: Optional[gpd.GeoDataFrame],
    trails_clip: gpd.GeoDataFrame,
    slope_result=None,
    confirmed_points=None,
    show_landform=False,
):
    """
    Plot study area with optional slope raster, trails, roads, and confirmed points.
    """
    fig, ax = _init_plot(figsize=(7, 7))

    if show_landform and slope_result is not None:
        _plot_slope(ax, fig, slope_result, cmap="terrain", label="Slope")
        ax.set_title("Slope and Networks")
    else:
        ax.set_title("Networks in the Study Area")

    _plot_roads_and_trails(ax, roads_clip, trails_clip, alpha_tr=0.8)
    _plot_confirmed_points(ax, confirmed_points)

    return fig, ax


def plot_segments_by_difficulty(
    segments: List[dict],
    trails_clip: gpd.GeoDataFrame,
    roads_clip: Optional[gpd.GeoDataFrame],
    start_point: Point,
    gdf_cells: Optional[gpd.GeoDataFrame] = None,
    process_buffer=False,
    gdf_study_points: Optional[gpd.GeoDataFrame] = None,
    plot_start_point=False,
    show_landform=False,
    slope_result = None
):
    """
    Plot trail segments colored by difficulty, with optional background cells,
    study points, and road/trail networks.
    """
    if not segments:
        logging.error("No segment to display.")
        return None

    fig, ax = _init_plot(figsize=(10, 10), title="Coloured segments by cumulative difficulty")

    if show_landform and slope_result is not None:
        _plot_slope(ax, fig, slope_result, cmap="terrain", label="Slope", alpha = 0.6)
        
    # --- Background cells (optional) ---
    if process_buffer:
        _plot_cells(ax, gdf_cells)

    # --- Segments ---
    _, sm = _plot_segments(ax, segments, cmap_name="rainbow")
    if sm is not None:
        cbar = fig.colorbar(sm, ax=ax)
        cbar.set_label("Difficulty of access to each trail segment")

    # --- Networks ---
    _plot_roads_and_trails(ax, roads_clip, trails_clip, 0.2)

    # --- Study points (optional) ---
    _plot_study_points(ax, gdf_study_points)

    # --- Start point (optional) ---
    if plot_start_point and start_point is not None:
        ax.plot(start_point.x, start_point.y, "rX", label="Start Point", zorder=12)

    plt.savefig("export/difficulty_map.png")
    return fig, ax
