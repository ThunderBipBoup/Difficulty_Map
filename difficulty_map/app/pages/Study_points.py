import os
import sys

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from mpl_toolkits.axes_grid1 import make_axes_locatable
from shapely.geometry import box

from difficulty_map.source import map_utils, pipeline
from difficulty_map.source.session_utils import init_session_state

# Import project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


if "has_initialized" not in st.session_state:
    init_session_state()
    st.session_state.has_initialized = True
bounds = st.session_state.study_area_geom.total_bounds
# ----------------------------
# Reset Button
# ----------------------------
if st.button("Reset all study points"):
    for key in [
        "random_points",
        "confirmed_points",
        "study_points_results",
        "num_points",
        "w_diff_on_tr",
        "w_diff_off_tr",
    ]:
        if key in st.session_state:
            st.session_state.pop(key)
    init_session_state()


# ----------------------------
# UI Section: Title + Input
# ----------------------------
st.title("Study Points")


# File uploader for CSV
uploaded_file = st.file_uploader("Import a CSV file of study points", type="csv")

if uploaded_file is not None:
    # Load uploaded CSV
    df = pd.read_csv(uploaded_file, sep=";")

    df.columns = df.columns.str.strip()

    # Vérifier colonnes X et Y
    if not all(col in df.columns for col in ["X", "Y"]):
        df = pd.read_csv(uploaded_file, sep=",")
        if not all(col in df.columns for col in ["X", "Y"]):
            st.error(
                "CSV must contain columns named exactly 'X' and 'Y'. The columns separator must be ';'."
            )
            st.stop()

    # Optionnel: ajouter une colonne Name si absente
    if "Name" not in df.columns:
        df["Name"] = [f"Point {i+1}" for i in range(len(df))]
    st.session_state.confirmed_points = df.copy()
    editor_data = df.copy()
else:
    # Number input synced with session state
    num_points = st.number_input(
        "Number of points",
        min_value=1,
        max_value=5000,
        value=st.session_state.num_points,
        step=1,
        key="num_points_input",
    )

    # Update session value if changed
    if num_points != st.session_state.num_points:
        st.session_state.num_points = num_points

    # ----------------------------
    # Generate random points
    # ----------------------------
    def generate_random_points(n, bounds):
        xmin, ymin, xmax, ymax = bounds
        xs = np.random.uniform(xmin, xmax, n)
        ys = np.random.uniform(ymin, ymax, n)
        return pd.DataFrame(
            [
                {"Name": f"Point {i+1}", "X": x, "Y": y}
                for i, (x, y) in enumerate(zip(xs, ys))
            ]
        )

    # ----------------------------
    # Determine editor data
    # ----------------------------
    if "confirmed_points" not in st.session_state:
        # No confirmed points, use or regenerate random
        if len(st.session_state.random_points) != num_points:
            st.session_state.random_points = generate_random_points(num_points, bounds)
        editor_data = st.session_state.random_points.copy()
    else:
        # Confirmed points exist, sync with number input
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

# ----------------------------
# Interactive Form
# ----------------------------
with st.form("edit_points_form"):
    st.write("Edit the study points below:")
    edited_data = st.data_editor(
        editor_data, num_rows="dynamic", use_container_width=True
    )
    submitted = st.form_submit_button("Confirm points")

if submitted:
    st.session_state.confirmed_points = edited_data.copy()
    st.success("Study points updated!")

# ----------------------------
# Map Display
# ----------------------------


st.title("Study Area Map")
show_landform = st.checkbox("Show slope (terrain background)")


trails, roads = pipeline.load_input_data()
roads_clip, trails_clip, slope_result = pipeline.study_area_displaying(
    trails, roads, st.session_state.study_area_geom, show_landform
)

fig, ax = plt.subplots(figsize=(7, 7))

if show_landform:
    slope_data, slope_extent = slope_result

    if slope_data is None or slope_extent is None or np.isnan(slope_data).all():
        st.warning("Slope data missing or invalid.")
    else:
        im = ax.imshow(
            slope_data,
            cmap="terrain",
            extent=slope_extent,  # [xmin, xmax, ymin, ymax]
            origin="upper",
            zorder=1,
        )

        ax.set_xlim(slope_extent[0], slope_extent[1])
        ax.set_ylim(slope_extent[2], slope_extent[3])

        ax.set_title("Slope and Networks")
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("bottom", size="5%", pad=0.4)
        cb = fig.colorbar(im, cax=cax, orientation="horizontal")
        cb.set_label("Slope (units)")
else:
    ax.set_title("Networks in the Study Area")


trails_clip.plot(ax=ax, color="black", linewidth=1, label="Trails", zorder=3)
roads_clip.plot(ax=ax, color="red", linewidth=2, label="Public Roads", zorder=4)

# Plot confirmed points
if not st.session_state.confirmed_points.empty:
    confirmed_data = st.session_state.confirmed_points
    gdf_points = gpd.GeoDataFrame(
        confirmed_data,
        geometry=gpd.points_from_xy(confirmed_data["X"], confirmed_data["Y"]),
        crs=map_utils.TARGET_CRS,
    )
    for idx, row in gdf_points.iterrows():
        ax.text(
            row.geometry.x + 50,
            row.geometry.y + 50,
            str(row["Name"]),
            fontsize=9,
            color="blue",
            zorder=6,
            bbox=dict(
                facecolor="ivory",  
                alpha=0.8,  
                edgecolor="none",
                boxstyle="round,pad=0.2",
            ),
        )

    gdf_points.plot(ax=ax, color="blue", marker="o", markersize=50, zorder=5)

st.pyplot(fig)

# ----------------------------
# Difficulty Table
# ----------------------------


st.sidebar.text(
    "For each point, \nTotal difficulty = \n( distance on trails x slope on trails x WEIGHT ON TRAILS ) \n+ \n( distance off trails x slope off trails x WEIGHT OFF TRAILS )"
)
w_diff_on_tr = st.sidebar.slider(
    "Weight on trails ",
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


# ---------- Helpers ----------
def _points_signature(df: pd.DataFrame, ndigits: int = 3):
    """Signature immuable des points confirmés (pour détecter les changements)."""
    if df is None or df.empty:
        return None
    return tuple(
        (round(float(x), ndigits), round(float(y), ndigits))
        for x, y in zip(df["X"], df["Y"])
    )


def _get_segments_from_cache():
    """Récupère des segments depuis le cache : priorise last_params_key, sinon dernière entrée."""
    cache = st.session_state.get("analysis_cache", {})
    if not cache:
        return None
    key = st.session_state.get("last_params_key")
    if key and key in cache:
        return cache[key][0]  # segments
    # fallback: dernière entrée insérée
    try:
        last_key = next(reversed(cache))
        st.session_state.last_params_key = (
            last_key  # on la mémorise pour la prochaine fois
        )
        return cache[last_key][0]
    except StopIteration:
        return None


# ---------- (Re)compute study points results if needed ----------
if not st.session_state.confirmed_points.empty:
    confirmed_df = st.session_state.confirmed_points.copy()
    current_sig = _points_signature(confirmed_df)
    last_sig = st.session_state.get("last_points_sig")
    last_weights = st.session_state.get("last_weights")

    segments = _get_segments_from_cache()

    # Conditions de recalcul :
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
        # Met à jour la trace du dernier calcul
        st.session_state.last_points_sig = current_sig
        st.session_state.last_weights = (
            st.session_state.w_diff_on_tr,
            st.session_state.w_diff_off_tr,
        )
    elif segments is None:
        st.warning("No cached analysis. First run the analysis on the main page.")
else:
    # Pas de points confirmés → on efface le tableau si besoin
    st.session_state.study_points_results = gpd.GeoDataFrame(
        columns=["geometry", "difficulty", "dist_road"], crs=map_utils.TARGET_CRS
    )


# ---------- Display table (Arrow-safe) ----------
if not st.session_state.study_points_results.empty:
    st.subheader("Study Points Difficulty Table")

    df = st.session_state.study_points_results.copy()
    # Convertit la géométrie en texte lisible (évite l’erreur Arrow)
    df["X"] = df.geometry.apply(lambda g: f"{g.x:.1f}" if g is not None else None)
    df["Y"] = df.geometry.apply(lambda g: f"{g.y:.1f}" if g is not None else None)
    df = df.drop(columns=["geometry"], errors="ignore")

    # Renomme les colonnes si elles existent
    rename_map = {
        "X": "X",
        "Y": "Y",
        "dist_road": "Road distance (m)",
        "dist_on_trails": "Trail distance (m)",
        "total_elev_gain": "Total ascending elevation (m)",
        "total_descent": "Total descending elevation (m)",
        "dist_out_trail": "Off-trail distance (m)",
        "diff_alt_w_trail": "Difference in altitude with closest trail (m)",
        "diff": "Total Difficulty",
    }

    existing_cols = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=existing_cols)

    # Réindexer à partir de 1
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
