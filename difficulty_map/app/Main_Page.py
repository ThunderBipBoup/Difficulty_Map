"""
    DIFFICULTY MAP

    Program that calculates the difficulty of accessing points on
    a map as a function of altitude, trails and roads.

    Copyright (C) 2025  Emma DELAHAIE

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
    
"""
    
import io
import logging
import os
import sys
import zipfile

import geopandas as gpd
import matplotlib.pyplot as plt
import streamlit as st
import rasterio
from shapely.geometry import LineString, Point, box
from rasterio.plot import show

# --------------------------
# Project Imports and Setup
# --------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from difficulty_map.logging_config import configure_logging
from difficulty_map.source import map_utils, pipeline, plot_utils
from difficulty_map.source.session_utils import init_session_state

configure_logging()

# --------------------------
# Load Input Data
# --------------------------
trails, roads = map_utils.read_and_prepare_layers()

# --------------------------
# Initialize Session State
# --------------------------
if "has_initialized" not in st.session_state:
    init_session_state()
    st.session_state.has_initialized = True

# --------------------------
# UI: Study Area Selection
# --------------------------
st.title("Select a Study Area")

if st.button("Reset all"):
    for key in [
        "side",
        "x_box",
        "y_box",
        "x_start_pt",
        "y_start_pt",
        "start_point",
        "tr_threshold",
        "ro_threshold",
        "start_point_user, study_area_geom",
    ]:
        if key in st.session_state:
            st.session_state.pop(key)
    init_session_state()

# Study area size
side = st.sidebar.number_input(
    "Study area side (m)",
    value=st.session_state.side,
    step=500,
)
st.session_state.side = side
half_side = side / 2

# Study area center
x_box = st.sidebar.number_input(
    "Study area center X", value=st.session_state.x_box, step=100
)
y_box = st.sidebar.number_input(
    "Study area center Y", value=st.session_state.y_box, step=100
)
st.session_state.x_box = x_box
st.session_state.y_box = y_box

st.sidebar.divider()

# Starting point
x_start_pt = st.sidebar.number_input(
    "Starting point X", value=st.session_state.x_start_pt, step=50
)
y_start_pt = st.sidebar.number_input(
    "Starting point Y", value=st.session_state.y_start_pt, step=50
)
st.session_state.x_start_pt = x_start_pt
st.session_state.y_start_pt = y_start_pt

# User-defined starting point
user_point = Point(x_start_pt, y_start_pt)

# Snap user point to the nearest road
projected_point = pipeline.project_point_on_nearest_road(roads, user_point)

# Store both in session state for later use
st.session_state["start_point_user"] = user_point
st.session_state["start_point"] = projected_point

st.sidebar.divider()

# Trail connection threshold
tr_threshold = st.sidebar.number_input(
    "Trail connection threshold (m)",
    min_value=0,
    max_value=1000,
    value=st.session_state.tr_threshold,
    step=5,
)
st.session_state.tr_threshold = tr_threshold

# Road connection threshold
ro_threshold = st.sidebar.number_input(
    "Road connection threshold (m)",
    min_value=0,
    max_value=1000,
    value=st.session_state.ro_threshold,
    step=5,
)
st.session_state.ro_threshold = ro_threshold


# Landform background option
show_landform = st.checkbox("Show slope (terrain background)")

# --------------------------
# Study Area Geometry
# --------------------------
study_area_box = box(
    x_box - half_side, y_box - half_side, x_box + half_side, y_box + half_side
)
st.session_state.study_area_geom = gpd.GeoDataFrame(
    geometry=[study_area_box], crs=map_utils.TARGET_CRS
)

# --------------------------
# Map Display
# --------------------------
fig, ax = plt.subplots(figsize=(10, 10))
if show_landform:
    with rasterio.open(map_utils.RASTER_PATH) as src:
        show(src, ax=ax, cmap="terrain")
        ax.grid(True, linewidth=0.5, linestyle="--", alpha=0.5)

trails.plot(ax=ax, color="purple", linewidth=0.7, label="Trails")
roads.plot(ax=ax, color="gold", linewidth=2, label="Public Roads")
st.session_state.study_area_geom.boundary.plot(ax=ax, color="red")

# Draw user and projected starting point
user_pt = st.session_state.get("start_point_user", None)
proj_pt = st.session_state.get("start_point", None)

if user_pt and proj_pt:
    ax.plot(*user_pt.xy, "k*", label="User Starting Point")
    ax.plot(*proj_pt.xy, "rX", label="Projected on Road")

    # Draw projection line
    line = LineString([user_pt, proj_pt])
    ax.plot(*line.xy, "k--", linewidth=1, label="Projection Line")

ax.legend()
ax.set_title("Study Area")
st.pyplot(fig)


# --------------------------
# Export Helper (ZIP)
# --------------------------
def zip_export_folder(folder_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_name in os.listdir(folder_path):
            full_path = os.path.join(folder_path, file_name)
            zipf.write(full_path, arcname=file_name)
    zip_buffer.seek(0)
    return zip_buffer


# --------------------------
# Buffer Settings
# --------------------------
process_buffer = st.checkbox(
    "Enable Buffer", value=st.session_state.process_buffer)
st.session_state.process_buffer = process_buffer

if process_buffer:
    buffer_width = st.number_input(
        "Buffer width (m)",
        min_value=0,
        max_value=5000,
        value=st.session_state.buffer_width,
        step=10,
    )
    cell_size = st.number_input(
        "Cell size (m)",
        min_value=1,
        max_value=1000,
        value=st.session_state.cell_size,
        step=10,
    )
    st.session_state.buffer_width = buffer_width
    st.session_state.cell_size = cell_size
else:
    buffer_width = None
    cell_size = None


# --------------------------
# Plot Wrapper for Segments
# --------------------------
def plot_segments_streamlit(*args, **kwargs):
    fig, _ = plot_utils.plot_segments_by_difficulty(*args, **kwargs)
    if fig is None:
        st.warning("Unable to generate the figure.")
    else:
        st.pyplot(fig)


# --------------------------
# Launch Analysis
# --------------------------
if st.button("Confirm Study Area and Starting Point"):
    st.success(f"Study area centered at ({x_box}, {y_box}) confirmed.")
    st.success(f"Starting point at ({x_start_pt}, {y_start_pt}) confirmed.")

    # Unique cache key for parameter combinations
    params_key = (
    f"{x_box}_{y_box}_{x_start_pt}_{y_start_pt}_"
    f"{side}_{process_buffer}_{buffer_width}_"
    f"{cell_size}_{tr_threshold}_{ro_threshold}"
)

    if params_key not in st.session_state.analysis_cache:
        with st.spinner("Running analysis..."):
            segments, trails_clip, roads_clip, gdf_cells, result = (
                pipeline.run_difficulty_analysis(
                    trails,
                    roads,
                    study_area_box,
                    st.session_state.start_point,
                    process_buffer,
                    buffer_width,
                    cell_size,
                    tr_threshold,
                    ro_threshold,
                    st.session_state.w_diff_on_tr,
                    st.session_state.w_diff_off_tr
                )
            )
            # Compute slope only once
            slope_result = map_utils.show_landform_utils(
                st.session_state.study_area_geom
            )

            st.session_state.analysis_cache[params_key] = (
                segments,
                trails_clip,
                roads_clip,
                gdf_cells,
                result,
                slope_result,
            )
            st.session_state["last_params_key"] = params_key
            st.success("Analysis complete.")
    else:
        segments, trails_clip, roads_clip, gdf_cells, result, slope_result = (
            st.session_state.analysis_cache[params_key]
        )
        st.info("Loaded from cache.")

    # Study points analysis
    if (
        "confirmed_points" not in st.session_state
        or st.session_state.confirmed_points.empty
    ):
        logging.info("No confirmed points.")
    else:
        confirmed_df = st.session_state.confirmed_points
        study_points = gpd.points_from_xy(confirmed_df["X"], confirmed_df["Y"])

        st.session_state.study_points_results = pipeline.analyze_study_points(
            study_points=study_points,
            segments=segments,
            w_diff_on_tr=st.session_state.w_diff_on_tr,
            w_diff_off_tr=st.session_state.w_diff_off_tr,
        )

# --------------------------
# Display Results (always shown if available)
# --------------------------
if "last_params_key" in st.session_state:
    segments, trails_clip, roads_clip, gdf_cells, result, slope_result = (
        st.session_state.analysis_cache[st.session_state["last_params_key"]]
    )

    plot_start_point = st.session_state.study_area_geom.contains(
        st.session_state.start_point
    ).values[0]

    plot_segments_streamlit(
        segments,
        trails_clip,
        roads_clip,
        st.session_state.start_point,
        gdf_cells,
        process_buffer,
        slope_result=slope_result,
        gdf_study_points=st.session_state.get("study_points_results"),
        plot_start_point=plot_start_point,
        show_landform=show_landform,
    )

    # Export results
    st.success("Results available for export.")
    zip_data = zip_export_folder("export")
    st.download_button(
        label="Download Results (.zip)",
        data=zip_data,
        file_name="difficulty_results.zip",
        mime="application/zip",
    )
