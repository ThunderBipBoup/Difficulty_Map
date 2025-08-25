import heapq
import time

import numpy as np
from shapely.geometry import LineString

from difficulty_map.source.roads import dist_on_road

# ===================================================== #
#   DISTANCE & GEOMETRY UTILITIES
# ===================================================== #


def build_segment(trail, current_dist, next_dist):
    """
    Build a trail segment (LineString) between two distances along the trail geometry.
    """
    pt_start = trail.geom.interpolate(current_dist)
    pt_end = trail.geom.interpolate(next_dist)
    return LineString([pt_start, pt_end])


def sample_valid_raster_values(segment, src, n_points):
    """
    Sample raster values along a trail segment.

    Parameters
    ----------
    segment : LineString
        Geometry of the segment.
    src : rasterio.DatasetReader
        Raster source containing elevation/slope values.
    n_points : int
        Number of points to sample along the segment.

    Returns
    -------
    np.ndarray
        Array of sampled values excluding nodata values.
    """
    distances = np.linspace(0, segment.length, n_points)
    coords = [(segment.interpolate(d).x, segment.interpolate(d).y) for d in distances]
    values = np.array([val[0] for val in src.sample(coords)])

    nodata = src.nodata if src.nodata is not None else -9999.0
    return values[values != nodata]


# ===================================================== #
#   INITIALIZATION
# ===================================================== #


def initialize_queue(starting_cps, roads, start_point):
    """
    Initialize the priority queue (min-heap) for Dijkstra's algorithm.

    Each starting cutting point is seeded with zero cost metrics.
    """
    queue = []
    for cp in starting_cps:
        cp.best_diff = 0
        cp.total_dist = 0
        cp.total_elev_gain = 0
        cp.total_descent = 0
        cp.dist_on_roads = dist_on_road(roads, cp, start_point)
        heapq.heappush(queue, cp)
    return queue


# ===================================================== #
#   CORE PROPAGATION LOGIC
# ===================================================== #


def compute_difficulty_between_points(src, cp, neighbor_cp, trail, n_points=50):
    """
    Compute the difficulty metrics between two cutting points on a given trail.

    A trail is divided into segments of fixed step size, and for each segment
    raster values are sampled to evaluate difficulty.

    Difficulty definition:
    - Segment difficulty (`seg_diff`) = distance cost + effect of elevation changes
      (ascents increase difficulty, descents reduce it).
    - Cumulative difficulty is propagated across segments.

    Returns
    -------
    results : list of dict
        Each dictionary stores metrics for one trail segment.
    difficulty_at_distances : dict
        Maps a position along the trail to cumulative difficulty.
    total_diff : float
        Final cumulative difficulty at neighbor_cp.
    direction : int
        Travel direction (+1 or -1).
    total_dist, total_elev_gain, total_descent : float
        Final cumulative metrics at neighbor_cp.
    """
    # Project both cutting points along trail geometry
    dist_cp = trail.geom.project(cp.geom)
    dist_neighbor = trail.geom.project(neighbor_cp.geom)

    min_dist = min(dist_cp, dist_neighbor)
    max_dist = max(dist_cp, dist_neighbor)

    # Segment size in projection units
    dist_step = 50
    current_dist = min_dist
    segments = []

    # Build contiguous segments along the trail
    while current_dist < max_dist:
        next_dist = min(current_dist + dist_step, max_dist)
        segment = build_segment(trail, current_dist, next_dist)
        segments.append(
            {"geometry": segment, "start_dist": current_dist, "end_dist": next_dist}
        )
        current_dist = next_dist

    # Determine direction of traversal
    direction = 1 if abs(dist_cp - min_dist) < 1e-6 else -1
    if direction == -1:
        segments = segments[::-1]

    # Initialize cumulative metrics from current cp
    total_diff = cp.best_diff
    total_dist = cp.total_dist
    total_elev_gain = cp.total_elev_gain
    total_descent = cp.total_descent

    difficulty_at_distances = {}
    results = []

    for seg in segments:
        values = sample_valid_raster_values(seg["geometry"], src, n_points)
        if len(values) == 0:
            continue

        segment_length = seg["geometry"].length
        # Difficulty for this segment = sum of absolute raster values
        seg_diff = np.nansum(np.abs(values))

        # Track elevation changes
        elevation_gain = 0
        descent = 0
        for i in range(1, len(values)):
            delta = values[i] - values[i - 1]
            if delta > 0:
                elevation_gain += delta
            else:
                descent += delta

        # Update cumulative totals
        total_diff += seg_diff
        total_dist += segment_length
        total_elev_gain += elevation_gain
        total_descent += descent

        # Key distance for ordering
        dist_key = seg["start_dist"] if direction == 1 else seg["end_dist"]

        # Store segment metrics
        results.append(
            {
                "geometry": seg["geometry"],
                "seg_diff": seg_diff,  # Difficulty for this segment
                "total_diff": total_diff,  # Cumulative difficulty
                "posit_seg": dist_key,  # Position key along trail
                "dist_road": cp.dist_on_roads,  # Road distance up to entry
                "trail_id": trail.id,
                "start_cp": cp,
                "end_cp": neighbor_cp,
                "segment_length": segment_length,
                "total_dist": total_dist,
                "elevation_gain": elevation_gain,
                "total_elev_gain": total_elev_gain,
                "descent": descent,
                "total_descent": total_descent,
            }
        )

        difficulty_at_distances[dist_key] = total_diff

    return (
        results,
        difficulty_at_distances,
        total_diff,
        total_dist,
        total_elev_gain,
        total_descent,
    )


def remove_segments_between(all_segments, trail_id, cp1, cp2):
    """
    Remove segments connecting two cutting points on the same trail
    from a list of segments.
    """
    return [
        seg
        for seg in all_segments
        if not (
            seg["trail_id"] == trail_id
            and (
                (seg["start_cp"] == cp1 and seg["end_cp"] == cp2)
                or (seg["start_cp"] == cp2 and seg["end_cp"] == cp1)
            )
        )
    ]


def process_neighbors(cp, queue, src, all_segments_dijk, trail_difficulty_by_distance):
    """
    Process all neighbors of a given cutting point in the Dijkstra expansion.
    Updates neighbor cutting points if a cheaper path is found.
    """
    for neighbor_cp, trail_list in cp.dict_neighbors.items():
        for trail in trail_list:
            (
                segments,
                diff_map,
                final_diff,
                total_dist,
                total_elev_gain,
                total_descent,
            ) = compute_difficulty_between_points(src, cp, neighbor_cp, trail)

            if neighbor_cp.best_diff >= final_diff:
                # Found a better path to neighbor_cp
                neighbor_cp.best_diff = final_diff
                neighbor_cp.dist_on_roads = cp.dist_on_roads
                neighbor_cp.total_dist = total_dist
                neighbor_cp.total_elev_gain = total_elev_gain
                neighbor_cp.total_descent = total_descent

                trail_difficulty_by_distance[trail] = diff_map
                if segments:
                    all_segments_dijk.extend(segments)

            else:
                # Check reverse direction if forward is worse
                segments_opp, diff_map_opp, final_diff_opp, _, _, _ = (
                    compute_difficulty_between_points(src, neighbor_cp, cp, trail)
                )

                if final_diff_opp > cp.best_diff:
                    merged_segments, merged_diff_map = merge_segments_and_difficulties(
                        segments, diff_map, segments_opp, diff_map_opp
                    )
                    trail_difficulty_by_distance[trail] = merged_diff_map
                    all_segments_dijk = remove_segments_between(
                        all_segments_dijk, trail.id, neighbor_cp, cp
                    ).copy()
                    all_segments_dijk.extend(merged_segments)

            heapq.heappush(queue, neighbor_cp)

    return all_segments_dijk


def dijkstra(starting_cps, src, roads, start_point):
    """
    Dijkstra-like algorithm for propagating trail difficulty from starting points.

    Returns
    -------
    all_segments_dijk : list of dict
        All computed trail segments with difficulty metrics.
    list_visited : list of CuttingPoint
        All cutting points visited during expansion.
    metrics : dict
        Execution metrics summary.
    """
    all_segments_dijk = []
    trail_difficulty_by_distance = {}
    queue = initialize_queue(starting_cps, roads, start_point)
    visited = set()
    list_visited = []

    start_time = time.time()

    while queue:
        cp = heapq.heappop(queue)

        if cp in visited:
            continue

        visited.add(cp)
        list_visited.append(cp)

        all_segments_dijk = process_neighbors(
            cp, queue, src, all_segments_dijk, trail_difficulty_by_distance
        )

    total_time = time.time() - start_time

    segment_difficulties = [seg["seg_diff"] for seg in all_segments_dijk]
    segment_difficulties = np.array(segment_difficulties)

    metrics = {
        "execution_time_sec": round(total_time, 2),
        "cutting_points_processed": len(list_visited),
        "segments_created": len(all_segments_dijk),
        "max_difficulty": (
            round(float(np.nanmax(segment_difficulties)), 2)
            if segment_difficulties.size > 0
            else None
        ),
        "avg_seg_diff": (
            round(float(np.nanmean(segment_difficulties)), 2)
            if segment_difficulties.size > 0
            else None
        ),
    }

    return all_segments_dijk, metrics


# ===================================================== #
#   MERGE LOGIC
# ===================================================== #


def merge_segments_and_difficulties(
    segments_fwd, diff_map_fwd, segments_bwd, diff_map_bwd
):
    """
    Merge two sets of segments and difficulty maps (forward and backward traversal).

    At each position, keeps the path with lower cumulative difficulty.
    """
    all_distances = sorted(set(diff_map_fwd.keys()) | set(diff_map_bwd.keys()))
    if not all_distances:
        return [], {}

    merged_diff_map = {}
    merged_segments = []

    seg_fwd_by_dist = {seg["posit_seg"]: seg for seg in segments_fwd}
    seg_bwd_by_dist = {seg["posit_seg"]: seg for seg in segments_bwd}

    for d in all_distances:
        val_fwd = diff_map_fwd.get(d, float("inf"))
        val_bwd = diff_map_bwd.get(d, float("inf"))

        if val_fwd <= val_bwd:
            merged_diff_map[d] = val_fwd
            seg = seg_fwd_by_dist.get(d)
        else:
            merged_diff_map[d] = val_bwd
            seg = seg_bwd_by_dist.get(d)

        if seg:
            merged_segments.append(seg)

    return merged_segments, merged_diff_map