import logging
import math

import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from shapely.geometry import LineString

from .roads import create_tab_dist_on_roads


def plot_segments_by_difficulty(
    segments, trails_clip, roads_clip, start_point,
    gdf_cells=None, process_buffer=False, points=False,
    gdf_study_points=None,plot_start_point=False
):
    if not segments:
        logging.error("No segment to display.")
        return None

    fig, ax = plt.subplots(figsize=(10, 10))

    # ---------- Background cells (optional) ----------
    if process_buffer and gdf_cells is not None:
        vmin = gdf_cells["difficulty"].quantile(0.05)
        vmax = gdf_cells["difficulty"].quantile(0.95)

        gdf_cells.plot(
            ax=ax,
            column="difficulty",
            cmap="rainbow",
            markersize=40,
            alpha=0.8,
            vmin=vmin,
            vmax=vmax
        )

    # ---------- Segments ----------
    difficulties = [seg["total_diff"] for seg in segments if "total_diff" in seg]
    if not difficulties:
        logging.error("No difficulties found in the segments.")
        return None

    vmin = min(difficulties)
    vmax = max(difficulties)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.rainbow

    for seg in segments:
        line: LineString = seg["geometry"]
        diff = seg["total_diff"]
        color = cmap(norm(diff))
        if isinstance(line, LineString):
            x, y = line.xy
            ax.plot(x, y, color=color, linewidth=2, alpha=0.2)
            ax.plot(x, y, color=color, linewidth=2)
        else:
            logging.warning(f"Segment geometry is not a LineString: {type(line)}")

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label("Difficulty of access to each segment of trails")

    # ---------- Trails & Roads ----------
    trails_clip.plot(ax=ax, color="black", linewidth=0.5, alpha=0.3)
    roads_clip.plot(ax=ax, color="pink", linewidth=4)

    # ---------- Graph points ----------
    """if points:
        tab_dist_on_roads = create_tab_dist_on_roads(graph)
        dist_roads_norm = mcolors.Normalize(vmin=min(tab_dist_on_roads), vmax=max(tab_dist_on_roads))
        dist_roads_cmap = cm.get_cmap('plasma')

        for cp in graph.nodes:
            if not math.isinf(cp.dist_on_roads):
                color = dist_roads_cmap(dist_roads_norm(cp.dist_on_roads))
                ax.plot(cp.geom.x, cp.geom.y, color=color, marker='o')
            else:
                ax.plot(cp.geom.x, cp.geom.y, 'ko')"""

    # ---------- Study points ----------
    if gdf_study_points is not None and not gdf_study_points.empty:
        if "diff" not in gdf_study_points.columns:
            logging.warning("La colonne 'diff' est manquante dans gdf_study_points.")
        else:
            vmin = gdf_study_points["diff"].min()
            vmax = gdf_study_points["diff"].max()
            sp_norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
            sp_cmap = cm.get_cmap("rainbow")

            gdf_study_points.plot(
                ax=ax,
                column="diff",
                cmap=sp_cmap,
                markersize=80,
                label='Distance driven on road',
                marker='o',
                linewidth=0.5,
                zorder=10
            )

    
    if plot_start_point:
        ax.plot(start_point.x, start_point.y, 'rX', label="Start Point")
    else:
        logging.info("Start point is outside of the study area.")

    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Coloured segments by cumulative difficulty")

    plt.savefig("export/difficulty_map.png")

    return fig, ax
