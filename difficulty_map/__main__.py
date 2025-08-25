import logging
from .source.pipeline import *

from difficulty_map.logging_config import configure_logging
configure_logging()


trails, roads = read_and_prepare_layers()

start_pt = Point(821000,5139000)

x_box, y_box = 819500, 5137500
side=3000

demi_side=side/2
small_box = box(x_box - demi_side, y_box - demi_side, x_box + demi_side, y_box + demi_side)

segments, graph, trails_clip, roads_clip,_ = run_difficulty_analysis(trails, roads, small_box, start_pt, process_buffer=False)
plot_segments_by_difficulty(segments, graph, trails_clip, roads_clip, start_pt, points=True, process_buffer=False)

