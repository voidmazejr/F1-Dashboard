import dearpygui.dearpygui as dpg
import numpy as np
import ui.state as state
from utils.colors import get_team_color, get_compound_color
from ui.helpers import normalize_coordinates


def to_canvas(x, y):
    if state.track_x is None or state.track_y is None:
        return 0.0, 0.0
    px = ((x - state.canvas_x_min) / (state.canvas_x_max - state.canvas_x_min)) * (state.CANVAS_WIDTH - 80) + 40
    py = state.CANVAS_HEIGHT - ((y - state.canvas_y_min) / (state.canvas_y_max - state.canvas_y_min)) * (state.CANVAS_HEIGHT - 80) - 40
    return px, py


def draw_track():
    dpg.delete_item("track_layer", children_only=True)

    if state.track_x is None or state.track_y is None:
        return

    tx = normalize_coordinates(state.track_x, 0, state.CANVAS_WIDTH)
    ty = normalize_coordinates(state.track_y, 0, state.CANVAS_HEIGHT)
    ty = state.CANVAS_HEIGHT - ty

    points = list(zip(tx.tolist(), ty.tolist()))
    points.append(points[0])

    for i in range(len(points) - 1):
        dpg.draw_line(points[i], points[i + 1], color=(80, 80, 80, 255), thickness=8, parent="track_layer")


def draw_pit_lane():
    if state.pit_x is None or state.pit_y is None or state.track_x is None or state.track_y is None:
        return

    distances_start = np.sqrt((state.track_x - state.pit_x[0])**2 + (state.track_y - state.pit_y[0])**2)
    nearest_start = np.argmin(distances_start)

    distances_end = np.sqrt((state.track_x - state.pit_x[-1])**2 + (state.track_y - state.pit_y[-1])**2)
    nearest_end = np.argmin(distances_end)

    tx_start, ty_start = to_canvas(state.track_x[nearest_start], state.track_y[nearest_start])
    px_start, py_start = to_canvas(state.pit_x[0], state.pit_y[0])
    dpg.draw_line((tx_start, ty_start), (px_start, py_start), color=(80, 80, 80, 255), thickness=5, parent="track_layer")

    for i in range(len(state.pit_x) - 1):
        px1, py1 = to_canvas(state.pit_x[i], state.pit_y[i])
        px2, py2 = to_canvas(state.pit_x[i + 1], state.pit_y[i + 1])
        dpg.draw_line((px1, py1), (px2, py2), color=(80, 80, 80, 255), thickness=5, parent="track_layer")

    tx_end, ty_end = to_canvas(state.track_x[nearest_end], state.track_y[nearest_end])
    px_end, py_end = to_canvas(state.pit_x[-1], state.pit_y[-1])
    dpg.draw_line((px_end, py_end), (tx_end, ty_end), color=(80, 80, 80, 255), thickness=5, parent="track_layer")


def create_driver_markers():
    state.driver_tags = {}
    dpg.delete_item("driver_layer", children_only=True)

    if not state.frames or state.session is None:
        return

    first_frame = state.frames[0]
    for car in first_frame["drivers"]:
        abbr = car["driver"]
        team = car["team"]

        hex_color = get_team_color(team, state.session)
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

        state.driver_tags[abbr] = {
            "circle": circle_tag,
            "label": label_tag,
            "color": (r, g, b)
        }


def apply_positions(positions: list):
    if state.track_x is None or state.track_y is None:
        return

    with state.render_mutex:
        for p in positions:
            if p["driver"] not in state.driver_tags:
                continue

            px = ((p["x"] - state.canvas_x_min) / (state.canvas_x_max - state.canvas_x_min)) * (state.CANVAS_WIDTH - 80) + 40
            py = state.CANVAS_HEIGHT - ((p["y"] - state.canvas_y_min) / (state.canvas_y_max - state.canvas_y_min)) * (state.CANVAS_HEIGHT - 80) - 40

            tags = state.driver_tags[p["driver"]]
            dpg.configure_item(tags["circle"], center=(px, py))
            dpg.configure_item(tags["label"], pos=(px + 10, py - 8))


def update_position_table():
    dpg.delete_item("position_table", children_only=True)

    if not state.frames or state.session is None:
        return

    if state.frame_index >= len(state.frames):
        return

    frame = state.frames[state.frame_index]
    race_elapsed = frame["t"] - state.race_start_time

    # First 20 seconds — use race_state
    if race_elapsed < 20.0 and state.race_state:
        source = state.race_state
        for entry in source:
            if entry["position"] == 99:
                continue
            team_hex = get_team_color(entry["team"], state.session)
            team_hex = team_hex.lstrip("#")
            r, g, b = tuple(int(team_hex[i:i+2], 16) for i in (0, 2, 4))
            compound_color = get_compound_color(entry["compound"])
            compound_letter = entry["compound"][0] if entry["compound"] not in ("?", "nan", "") else "?"
            with dpg.group(horizontal=True, parent="position_table"):
                dpg.add_text(f"{entry['position']:>2}", color=(255, 255, 255, 255))
                dpg.add_text(f" {entry['driver']}", color=(r, g, b, 255))
                dpg.add_text(f" {compound_letter}", color=compound_color)
        return

    # After 20 seconds — use frame positions directly
    for car in frame["drivers"]:
        abbr = car["driver"]
        team = car["team"]
        compound = car["compound"]
        position = car["position"]

        team_hex = get_team_color(team, state.session)
        team_hex = team_hex.lstrip("#")
        r, g, b = tuple(int(team_hex[i:i+2], 16) for i in (0, 2, 4))

        compound_color = get_compound_color(compound)
        compound_letter = compound[0] if compound not in ("?", "nan", "") else "?"

        with dpg.group(horizontal=True, parent="position_table"):
            dpg.add_text(f"{position:>2}", color=(255, 255, 255, 255))
            dpg.add_text(f" {abbr}", color=(r, g, b, 255))
            dpg.add_text(f" {compound_letter}", color=compound_color)