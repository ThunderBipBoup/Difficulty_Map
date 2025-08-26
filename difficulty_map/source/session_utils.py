import geopandas as gpd
import streamlit as st
from shapely.geometry import Point, box

from difficulty_map.source import map_utils


def init_session_state():
    # Load reference data
    trails, _ = map_utils.read_and_prepare_layers()
    xmin, ymin, xmax, ymax = trails.total_bounds
    x_center = int((xmin + xmax) // 2)
    y_center = int((ymin + ymax) // 2)

    defaults = {
        "side": 3000,
        "x_box": x_center,
        "y_box": y_center,
        "x_start_pt": x_center - 1000,
        "y_start_pt": y_center + 1000,
        "threshold_btw_cp": 50,
        "process_buffer": False,
        "buffer_width": 60,
        "cell_size": 20,
        "num_points": 3,
        "w_diff_on_tr": 0.5,
        "w_diff_off_tr": 0.5,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if (
        "study_area_geom" not in st.session_state
        or st.session_state.study_area_geom is None
    ):
        half = st.session_state.side / 2
        default_box = box(
            st.session_state.x_box - half,
            st.session_state.y_box - half,
            st.session_state.x_box + half,
            st.session_state.y_box + half,
        )
        st.session_state.study_area_geom = gpd.GeoDataFrame(
            geometry=[default_box], crs=map_utils.TARGET_CRS
        )

    if "start_point" not in st.session_state or st.session_state.start_point is None:
        st.session_state.start_point = Point(
            st.session_state.x_start_pt, st.session_state.y_start_pt
        )

    if "analysis_cache" not in st.session_state:
        st.session_state.analysis_cache = {}

    if "random_points" not in st.session_state:
        st.session_state.random_points = map_utils.generate_initial_points(
            st.session_state.study_area_geom.total_bounds, num_points=3
        )
