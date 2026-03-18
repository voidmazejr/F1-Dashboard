import dearpygui.dearpygui as dpg
import numpy as np
import ui.state as state
from utils.colors import get_team_color, get_compound_color
from ui.helpers import get_pos_at_time, normalize_coordinates, calculate_realtime_gaps



def to_canvas(x, y):
    if state.track_x is None or state.track_y is None:
        return 0.0, 0.0
    x_min, x_max = state.track_x.min(), state.track_x.max()
    y_min, y_max = state.track_y.min(), state.track_y.max()
    px = ((x - x_min) / (x_max - x_min)) * (state.CANVAS_WIDTH - 80) + 40
    py = state.CANVAS_HEIGHT - ((y - y_min) / (y_max - y_min)) * (state.CANVAS_HEIGHT - 80) - 40
    return px, py


def draw_track():
    dpg.delete_item("track_layer", children_only=True)

    if state.track_x is None or state.track_y is None:
        return

    tx = normalize_coordinates(state.track_x, 0, state.CANVAS_WIDTH)
    ty = normalize_coordinates(state.track_y, 0, state.CANVAS_HEIGHT)
    ty = state.CANVAS_HEIGHT - ty


    points = list(zip(tx.tolist(), ty.tolist()))
    points.append(points[0]) # close the track loop 

    for i in range(len(points) - 1):
        dpg.draw_line(points[i], points[i + 1], color=(80, 80, 80, 255), thickness=8, parent="track_layer")


def create_driver_markers():
    state.driver_tags = {}
    dpg.delete_item("driver_layer", children_only=True)

    if state.session is None:
        return

    for driver_num, driver_data in state.all_positions.items():
        abbr = driver_data["abbreviation"]

        hex_color = get_team_color(driver_data["team"], state.session)
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
    
    x_min, x_max = state.track_x.min(), state.track_x.max()
    y_min, y_max = state.track_y.min(), state.track_y.max()

    with state.render_mutex:
        for p in positions:
            if p["driver"] not in state.driver_tags:
                continue

            px = ((p["x"] - x_min) / (x_max - x_min)) * (state.CANVAS_WIDTH - 80) + 40
            py = state.CANVAS_HEIGHT - ((p["y"] - y_min) / (y_max - y_min)) * (state.CANVAS_HEIGHT - 80) - 40

            # Skip if position hasn't changed
            last = state.last_positions.get(p["driver"])
            if last and abs(last[0] - px) < 0.5 and abs(last[1] - py) < 0.5:
                continue

            state.last_positions[p["driver"]] = (px, py)
            tags = state.driver_tags[p["driver"]]
            dpg.configure_item(tags["circle"], center=(px, py))
            dpg.configure_item(tags["label"], pos=(px + 10, py - 8))


def update_driver_positions(current_time: float):
    positions = get_pos_at_time(state.all_positions, current_time)
    apply_positions(positions)


def update_position_table():
    dpg.delete_item("position_table", children_only=True)

    if not state.all_positions or state.session is None:
        return

    gaps = calculate_realtime_gaps(state.all_positions, state.current_time, state.race_state, state.lap_timestamps)

    if not gaps:
        return

    # Check if we're in pre-race mode (race_state order) or live mode (distance order)
    leader_dist = 0.0
    for driver_data in state.all_positions.values():
        times = driver_data["times"]
        dists = driver_data["distances"]
        if len(times) > 0 and len(dists) > 0:
            d = float(np.interp(state.current_time, times, dists))
            if d > leader_dist:
                leader_dist = d

    if leader_dist < 1000:
        # Pre-race — use race_state order
        entries = [(e["driver"], e["position"], gaps.get(e["driver"], "—")) 
                   for e in state.race_state if e["position"] != 99]
        entries.sort(key=lambda x: x[1])
    else:
        # Live mode — use distance order from gaps
        def sort_key(item):
            abbr, gap = item
            if gap == "Leader": return 0.0
            if gap in ("—", "N/A"): return 999.0
            if "L" in gap:
                try: return 500.0 + float(gap.replace("+", "").replace("L", ""))
                except: return 500.0
            try: return float(gap.replace("+", "").replace("s", ""))
            except: return 999.0

        sorted_gaps = sorted(gaps.items(), key=sort_key)
        entries = [(abbr, pos + 1, gap) for pos, (abbr, gap) in enumerate(sorted_gaps)]

    for pos, (abbr, _, gap) in enumerate(entries, start=1):
        driver_data = next((d for d in state.all_positions.values() if d["abbreviation"] == abbr), None)
        if not driver_data:
            continue

        team_hex = get_team_color(driver_data["team"], state.session)
        team_hex = team_hex.lstrip("#")
        r, g, b = tuple(int(team_hex[i:i+2], 16) for i in (0, 2, 4))

        race_entry = next((e for e in state.race_state if e["driver"] == abbr), None)
        compound = race_entry["compound"] if race_entry else "?"
        compound_letter = compound[0] if compound != "?" else "?"
        compound_color = get_compound_color(compound)

        with dpg.group(horizontal=True, parent="position_table"):
            dpg.add_text(f"{pos:>2}", color=(255, 255, 255, 255))
            dpg.add_text(f" {abbr}", color=(r, g, b, 255))
            dpg.add_text(f" {compound_letter}", color=compound_color)
            dpg.add_text(f" {gap}", color=(180, 180, 180, 255))