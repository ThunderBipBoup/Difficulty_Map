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
import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from difficulty_map.source import map_utils, pipeline, plot_utils
from difficulty_map.source.session_utils import init_session_state

# Add project root to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


# --------------------------
# Initialize session state
# --------------------------
if "has_initialized" not in st.session_state:
    init_session_state()
    st.session_state.has_initialized = True

bounds = st.session_state.study_area_geom.total_bounds


# --------------------------
# UI Section: Title + Input
# --------------------------
st.title("Study Points")

# Reset button
if st.button("Reset all study points"):
    for key_cache in [
        "random_points",
        "confirmed_points",
        "study_points_results",
        "num_points",
        "w_diff_on_tr",
        "w_diff_off_tr",
    ]:
        if key_cache in st.session_state:
            st.session_state.pop(key_cache)
    init_session_state()

# File uploader for CSV
uploaded_file = st.file_uploader("Import a CSV file of study points", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, sep=";")
    df.columns = df.columns.str.strip()

    # Check for X and Y columns
    if not all(col in df.columns for col in ["X", "Y"]):
        df = pd.read_csv(uploaded_file, sep=",")
        if not all(col in df.columns for col in ["X", "Y"]):
            st.error(
                "CSV must contain columns named exactly 'X' and 'Y'. "
                "The column separator must be ';'."
            )
            st.stop()

    # Add a "Name" column if missing
    if "Name" not in df.columns:
        df["Name"] = [f"Point {i+1}" for i in range(len(df))]

    st.session_state.confirmed_points = df.copy()
    editor_data = df.copy()

else:
    # Input: number of points (linked to session state)
    num_points = st.number_input(
        "Number of points",
        min_value=1,
        max_value=5000,
        value=st.session_state.num_points,
        step=1,
        key="num_points_input",
    )

    # Sync session state value if changed
    if num_points != st.session_state.num_points:
        st.session_state.num_points = num_points

    # Helper: generate random points
    def generate_random_points(n, bounds):
        xmin, ymin, xmax, ymax = bounds
        xs = np.random.uniform(xmin, xmax, n)
        ys = np.random.uniform(ymin, ymax, n)
        return pd.DataFrame(
            [{"Name": f"Point {i+1}", "X": x, "Y": y} for i, (x, y) in enumerate(zip(xs, ys))]
        )

    if "confirmed_points" not in st.session_state:
        # No confirmed points → use or regenerate random
        if len(st.session_state.random_points) != num_points:
            st.session_state.random_points = generate_random_points(num_points, bounds)
        editor_data = st.session_state.random_points.copy()
    else:
        # Confirmed points exist → sync with number input
        confirmed = st.session_state.confirmed_points.copy()
        current_n = len(confirmed)

        if num_points > current_n:
            # Add new random points
            new_points = generate_random_points(num_points - current_n, bounds)
            new_points["Name"] = [f"Point {i+1}" for i in range(current_n, num_points)]
            confirmed = pd.concat([confirmed, new_points], ignore_index=True)

        elif num_points < current_n:
            confirmed = confirmed.iloc[:num_points].copy()

        editor_data = confirmed.copy()


# --------------------------
# Interactive form for editing points
# --------------------------
with st.form("edit_points_form"):
    st.write("Edit the study points below:")
    edited_data = st.data_editor(
        editor_data, num_rows="dynamic", use_container_width=True
    )
    submitted = st.form_submit_button("Confirm points")

if submitted:
    st.session_state.confirmed_points = edited_data.copy()
    st.success("Study points updated!")


# --------------------------
# Map display
# --------------------------
st.title("Study Area Map")
show_landform = st.checkbox("Show slope (terrain background)")

trails, roads = map_utils.read_and_prepare_layers()

fig, ax = plt.subplots(figsize=(7, 7))

study_area = st.session_state.study_area_geom
roads_clip, trails_clip = map_utils.clip_layers([roads, trails], study_area)

confirmed_points = (
    st.session_state.confirmed_points if "confirmed_points" in st.session_state else None
)

fig, ax = plot_utils.plot_study_area(
    roads_clip=roads_clip,
    trails_clip=trails_clip,
    slope_result=map_utils.show_landform_utils(study_area),
    confirmed_points=confirmed_points,
    show_landform=show_landform,
)

st.pyplot(fig)


# --------------------------
# Difficulty table: weights and formula
# --------------------------
st.sidebar.text(
    "Difficulty formula:\n"
    "(distance on trails × slope on trails × WEIGHT ON TRAILS)\n"
    "+\n"
    "(distance off trails × slope off trails × WEIGHT OFF TRAILS)"
)

w_diff_on_tr = st.sidebar.slider(
    "Weight on trails",
    min_value=0.0,
    max_value=1.0,
    value=st.session_state.w_diff_on_tr,
    step=0.05,
)
w_diff_off_tr = st.sidebar.slider(
    "Weight off trails",
    min_value=0.0,
    max_value=1.0,
    value=st.session_state.w_diff_off_tr,
    step=0.05,
)

st.session_state.w_diff_on_tr = w_diff_on_tr
st.session_state.w_diff_off_tr = w_diff_off_tr


# --------------------------
# Helpers
# --------------------------
def _points_signature(df: pd.DataFrame, ndigits: int = 3):
    """Immutable signature of confirmed points (used to detect changes)."""
    if df is None or df.empty:
        return None
    return tuple(
        (round(float(x), ndigits), round(float(y), ndigits))
        for x, y in zip(df["X"], df["Y"])
    )


def _get_segments_from_cache():
    """Retrieve segments from cache: prioritize last_params_key, else use most recent."""
    cache = st.session_state.get("analysis_cache", {})
    if not cache:
        return None
    key = st.session_state.get("last_params_key")
    if key and key in cache:
        return cache[key][0]  # segments
    # fallback: use most recent entry
    try:
        last_key = next(reversed(cache))
        st.session_state.last_params_key = last_key
        return cache[last_key][0]
    except StopIteration:
        return None


# --------------------------
# Recompute study point results if needed
# --------------------------
if "confirmed_points" in st.session_state:
    confirmed_df = st.session_state.confirmed_points.copy()
    current_sig = _points_signature(confirmed_df)
    last_sig = st.session_state.get("last_points_sig")
    last_weights = st.session_state.get("last_weights")

    segments = _get_segments_from_cache()

    # Recompute conditions
    need_recompute = segments is not None and (
        current_sig != last_sig
        or last_weights
        != (st.session_state.w_diff_on_tr, st.session_state.w_diff_off_tr)
    )

    if need_recompute:
        current_points = gpd.points_from_xy(
            confirmed_df["X"], confirmed_df["Y"], crs=map_utils.TARGET_CRS
        )
        st.session_state.study_points_results = pipeline.analyze_study_points(
            study_points=current_points,
            segments=segments,
            w_diff_on_tr=st.session_state.w_diff_on_tr,
            w_diff_off_tr=st.session_state.w_diff_off_tr,
        )
        # Update last computation state
        st.session_state.last_points_sig = current_sig
        st.session_state.last_weights = (
            st.session_state.w_diff_on_tr,
            st.session_state.w_diff_off_tr,
        )
    elif segments is None:
        st.warning("No cached analysis. First run the analysis on the main page.")
else:
    # No confirmed points → clear the table
    st.session_state.study_points_results = gpd.GeoDataFrame(
        columns=["geometry", "difficulty", "dist_road"], crs=map_utils.TARGET_CRS
    )


# --------------------------
# Display results table
# --------------------------
if not st.session_state.study_points_results.empty:
    st.subheader("Study Points Difficulty Table")

    df = st.session_state.study_points_results.copy()

    # Convert geometry into readable text (prevents Arrow serialization issues)
    df["X"] = df.geometry.apply(lambda g: f"{g.x:.1f}" if g is not None else None)
    df["Y"] = df.geometry.apply(lambda g: f"{g.y:.1f}" if g is not None else None)
    df = df.drop(columns=["geometry"], errors="ignore")

    # Rename columns if they exist
    rename_map = {
        "X": "X",
        "Y": "Y",
        "dist_road": "Road distance (m)",
        "dist_on_trails": "Trail distance (m)",
        "total_elev_gain": "Total ascending elevation (m)",
        "tot_desc": "Total descending elevation (m)",
        "dist_out_trail": "Off-trail distance (m)",
        "diff_alt_w_trail": "Altitude difference with closest trail (m)",
        "diff": "Total Difficulty",
    }

    existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_cols)

    # Reindex starting from 1
    df.index = range(1, len(df) + 1)

    cols_order = ["X", "Y"] + [col for col in df.columns if col not in ["X", "Y"]]
    df = df[cols_order]

    st.dataframe(df)

    st.download_button(
        "Download results (CSV)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="study_points_results.csv",
        mime="text/csv",
        key="download-study-points-csv",
    )
