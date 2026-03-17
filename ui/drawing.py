import dearpygui.dearpygui as dpg
import numpy as np
import ui.globals as globals
from utils.colors import get_team_color
from ui.helpers import get_pos_at_time, normalize_coordinates



def to_canvas(x, y):
    if globals.track_x is None or globals.track_y is None:
        return 0.0, 0.0
    x_min, x_max = globals.track_x.min(), globals.track_x.max()
    y_min, y_max = globals.track_y.min(), globals.track_y.max()
    px = ((x - x_min) / (x_max - x_min)) * (globals.CANVAS_WIDTH - 80) + 40
    py = globals.CANVAS_HEIGHT - ((y - y_min) / (y_max - y_min)) * (globals.CANVAS_HEIGHT - 80) - 40
    return px, py


def draw_track():
    dpg.delete_item("track_layer", children_only=True)

    if globals.track_x is None or globals.track_y is None:
        return

    tx = normalize_coordinates(globals.track_x, 0, globals.CANVAS_WIDTH)
    ty = normalize_coordinates(globals.track_y, 0, globals.CANVAS_HEIGHT)
    ty = globals.CANVAS_HEIGHT - ty

    points = list(zip(tx.tolist(), ty.tolist()))

    for i in range(len(points) - 1):
        dpg.draw_line(points[i], points[i + 1], color=(80, 80, 80, 255), thickness=8, parent="track_layer")


def create_driver_markers():
    globals.driver_tags = {}
    dpg.delete_item("driver_layer", children_only=True)

    if globals.session is None:
        return

    for driver_num, driver_data in globals.all_positions.items():
        abbr = driver_data["abbreviation"]

        hex_color = get_team_color(driver_data["team"], globals.session)
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        circle_tag = f"circle_{abbr}"
        label_tag = f"label_{abbr}"

        dpg.draw_circle(
            (-100, -100),
            radius=7,
            color=(r, g, b, 255),
            fill=(r, g, b, 255),
            parent="driver_layer",
            tag=circle_tag
        )
        dpg.draw_text(
            (-100, -100),
            abbr,
            color=(255, 255, 255, 220),
            size=12,
            parent="driver_layer",
            tag=label_tag
        )

        globals.driver_tags[abbr] = {
            "circle": circle_tag,
            "label": label_tag,
            "color": (r, g, b)
        }


def update_driver_positions(current_time: float):
    if globals.session is None or globals.track_x is None or globals.track_y is None:
        return

    positions = get_pos_at_time(globals.all_positions, current_time)

    x_min, x_max = globals.track_x.min(), globals.track_x.max()
    y_min, y_max = globals.track_y.min(), globals.track_y.max()

    with globals.render_mutex:
        for p in positions:
            if p["driver"] not in globals.driver_tags:
                continue

            px = ((p["x"] - x_min) / (x_max - x_min)) * (globals.CANVAS_WIDTH - 80) + 40
            py = globals.CANVAS_HEIGHT - ((p["y"] - y_min) / (y_max - y_min)) * (globals.CANVAS_HEIGHT - 80) - 40

            tags = globals.driver_tags[p["driver"]]
            dpg.configure_item(tags["circle"], center=(px, py))
            dpg.configure_item(tags["label"], pos=(px + 10, py - 8))