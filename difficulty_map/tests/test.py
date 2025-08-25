import matplotlib.pyplot as plt
import random
import unittest
#import difficulty_map

"""def find_connected_components(graph):
    visited = set()
    components = []
    
    for node in graph.nodes:
        if node not in visited:
            comp_visited = set()
            def dfs_comp(n):
                comp_visited.add(n)
                for neighbor in graph.edges[n]:
                    if neighbor not in comp_visited:
                        dfs_comp(neighbor)
            dfs_comp(node)
            visited.update(comp_visited)
            components.append(comp_visited)
    return components




def random_color():
    return (random.random(), random.random(), random.random())



def plot_test(graph,trails_clip):
    components = find_connected_components(graph)
    
    print(f"Nombre de composantes connexes : {len(components)}")
    for i, comp in enumerate(components, 1):
        print(f"  Composante {i} ({len(comp)} noeuds): {comp}")


    colors = [random_color() for _ in range(len(components))]
    
    plt.figure(figsize=(10,10))
    plt.title("Composantes connexes du graphe")
    
    trails_clip.plot(color="black", linewidth=0.5, alpha=0.3)
    
    for i, comp in enumerate(components):
        color = colors[i]
        xs = [node.geom.x for node in comp]
        ys = [node.geom.y for node in comp]
        plt.scatter(xs, ys, color=color, label=f"Composante {i+1} ({len(comp)})")
        
    
        # tracer les arêtes dans cette composante
        for node in comp:
            for neighbor in graph.edges.get(node, []):
                if neighbor in comp:
                    plt.plot([node.geom.x, neighbor.geom.x], [node.geom.y, neighbor.geom.y], color=color, alpha=0.5)

    plt.xlabel("x")
    plt.ylabel("y")
    plt.grid(True)
    plt.show()
"""

"""
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from shapely.geometry import box
import geopandas as gpd
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector
from shapely.geometry import box
from ..source.map_utils import *

src = rasterio.open(RASTER_PATH)


trails, roads = read_and_prepare_layers()
bbox, study_area = create_bounding_box(side=3000, x_start=819500, y_start = 5137500)


roads_clip, trails_clip = clip_layers([roads, trails], study_area)


fig, ax = plt.subplots(figsize=(10,10))

trails.plot(ax=ax, cmap="rainbow", linewidth=0.7, label="trails")
roads.plot(ax=ax, color="gold", linewidth=2, label="Public roads")


ax.legend()
ax.set_title("Trails and roads with study area")


rect_geometry = []

def onselect(eclick, erelease):
    x0, y0 = eclick.xdata, eclick.ydata
    x1, y1 = erelease.xdata, erelease.ydata
    bbox = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    rect_geometry.clear()
    rect_geometry.append(bbox)
    print(f"📦 Rectangle sélectionné : {bbox.bounds}")
    plt.close(fig)  # Ferme la figure après sélection

toggle_selector = RectangleSelector(ax, onselect, useblit=True,
                                    button=[1], minspanx=5, minspany=5,
                                    spancoords='data', interactive=True)

plt.show()

# Ensuite tu fais :
if rect_geometry:
    zone = rect_geometry[0]
    # Appel de ton pipeline
    # e.g. difficulty_map(zone, threshold=20)
"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Button, RectangleSelector
from shapely.geometry import box

fig, ax = plt.subplots()
plt.title("Déplacez le rectangle puis cliquez sur Valider")

# Rectangle de taille fixe (par exemple 1x1 unité)
rect = plt.Rectangle((0.5, 0.5), 1, 1, fill=False, color='red')
ax.add_patch(rect)

def onselect(eclick, erelease):
    print(f"Rectangle sélectionné: {eclick.xdata}, {eclick.ydata} -> {erelease.xdata}, {erelease.ydata}")

# Bouton "Valider"
def on_button_clicked(event):
    x, y = rect.get_xy()
    width, height = rect.get_width(), rect.get_height()
    print(f"Zone validée: {x}, {y}, {x+width}, {y+height}")
    # Ici tu peux déclencher ton calcul avec la zone

button_ax = plt.axes([0.8, 0.025, 0.1, 0.04])
button = Button(button_ax, 'Valider')
button.on_clicked(on_button_clicked)

plt.axis([0, 10, 0, 10])
plt.show()
