import dearpygui.dearpygui as dpg
import numpy as np
from fastf1.core import Session
from data.loader import load_session, get_track_outline, get_all_driver_positions, get_race_start_time, get_lap_timestamps
from utils.colors import get_team_color 
from typing import Optional
import threading
import time


CANVAS_WIDTH = 900
CANVAS_HEIGHT = 700

session: Optional[Session] = None
track_x: Optional[np.ndarray] = None
track_y: Optional[np.ndarray] = None
circuit_info = None
current_time: float = 0.0
max_time: float = 0.0
race_start_time: float = 0.0
animation_speed: float = 1.0
last_frame_time: float = 0.0
is_playing: bool = False
render_mutex = threading.Lock()
all_positions: dict = {}
lap_timestamps: list = []
driver_tags: dict = {}



def normalize_coordiantes(values, target_min: float, target_max: float, padding: float = 40):
    if values is None or len(values) == 0:
        return np.array([])

    min_val = values.min()
    max_val = values.max()

    scaled = ((target_max - target_min - padding * 2) / (max_val - min_val)) * (values - min_val) + target_min + padding
    return scaled


def get_pos_at_time(all_positions: dict, current_time: float):
    positions = []

    for driver_num, driver_data in all_positions.items():
        frames = driver_data["frames"]
        times = driver_data["times"]

        if len(frames) == 0:
            continue

        idx = int(np.searchsorted(times, current_time))
        idx = min(idx, len(frames) - 1)

        positions.append({
            "driver": driver_data["abbreviation"],
            "team": driver_data["team"],
            "x": frames[idx]["x"],
            "y": frames[idx]["y"],
        })

    return positions


def draw_track():
    dpg.delete_item("track_layer", children_only=True)

    if track_x is None or track_y is None:
        return

    tx = normalize_coordiantes(track_x, 0, CANVAS_WIDTH)
    ty = normalize_coordiantes(track_y, 0, CANVAS_HEIGHT)

    ty = CANVAS_HEIGHT - ty

    points = list(zip(tx.tolist(), ty.tolist()))

    for i in range(len(points) - 1):
        dpg.draw_line(points[i], points[i + 1], color=(80, 80, 80, 255), thickness=8, parent="track_layer")
    

def create_driver_markers():
    global driver_tags
    dpg.delete_item("driver_layer", children_only=True)
    driver_tags = {}

    if session is None:
        return

    for driver_num, driver_data in all_positions.items():
        abbr = driver_data["abbreviation"]

        hex_color = get_team_color(driver_data["team"], session)
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

        driver_tags[abbr] = {
            "circle": circle_tag,
            "label": label_tag,
            "color": (r, g, b)
        }


def update_driver_positions(time: float):
    if session is None or track_x is None or track_y is None:
        return

    positions = get_pos_at_time(all_positions, time)

    x_min, x_max = track_x.min(), track_x.max()
    y_min, y_max = track_y.min(), track_y.max()

    with render_mutex:
        for p in positions:
            if p["driver"] not in driver_tags:
                continue

            px = ((p["x"] - x_min) / (x_max - x_min)) * (CANVAS_WIDTH - 80) + 40
            py = CANVAS_HEIGHT - ((p["y"] - y_min) / (y_max - y_min)) * (CANVAS_HEIGHT - 80) - 40

            tags = driver_tags[p["driver"]]
            dpg.configure_item(tags["circle"], center=(px, py))
            dpg.configure_item(tags["label"], pos=(px + 10, py - 8))


def on_load_session(sender, app_data):
    global session, track_x, track_y, circuit_info, all_positions, current_time, max_time, race_start_time, lap_timestamps

    year = int(dpg.get_value("year_input"))
    grand_prix = dpg.get_value("gp_input")
    session_type = dpg.get_value("session_input")

    try:
        dpg.set_value("status_text", "Loading session...")

        session = load_session(year, grand_prix, session_type)

        if session is None:
            dpg.set_value("status_text", "Error: Could not load session")
            return

        track_x, track_y, circuit_info = get_track_outline(session)
        all_positions = get_all_driver_positions(session)
        race_start_time = get_race_start_time(session)
        current_time = race_start_time
        lap_timestamps = get_lap_timestamps(session)

        # Compute max time across all drivers
        max_time = max(
            f["time"]
            for driver_data in all_positions.values()
            for f in driver_data["frames"]
        )

        dpg.configure_item("time_slider", min_value=0.0)
        dpg.configure_item("time_slider", max_value=float(max_time-race_start_time))
        dpg.set_value("status_text", f"Loaded: {grand_prix} {year}")

        draw_track()
        create_driver_markers()
        update_driver_positions(current_time)
        build_lap_buttons()
        
    except Exception as e:
        dpg.set_value("status_text", f"Error loading session: {str(e)}")


def format_race_time(seconds: float):
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def animation_loop():
    global current_time, is_playing, last_frame_time

    if max_time is None or current_time is None or race_start_time is None:
        return
    if not is_playing:
        last_frame_time = 0.0
        return
    if current_time >= max_time:
        is_playing = False
        dpg.set_value("play_button", "Play")
        return

    now = time.time()
    if last_frame_time == 0.0:
        last_frame_time = now

    delta = now - last_frame_time  # actual seconds since last frame
    last_frame_time = now

    current_time += delta * animation_speed
    dpg.set_value("time_slider", current_time - race_start_time)
    dpg.set_value("time_display", format_race_time(current_time - race_start_time))
    update_driver_positions(current_time)


def on_play_pause(sender, app_data):
    global is_playing

    is_playing = not is_playing
    dpg.set_value("play_button", "Pause" if is_playing else "Play")


def on_time_change(sender, app_data):
    global current_time
    current_time = float(app_data) + race_start_time  # ← convert back to absolute
    dpg.set_value("time_display", format_race_time(float(app_data)))
    update_driver_positions(current_time)


def jump_to_time(absolute_time: float):
    global current_time
    current_time = absolute_time
    relative = absolute_time - race_start_time
    dpg.set_value("time_slider", relative)
    dpg.set_value("time_display", format_race_time(relative))
    update_driver_positions(current_time)


def on_toggle_laps(sender, app_data):
    config = dpg.get_item_configuration("lap_buttons_group")
    is_shown = config["show"]
    dpg.configure_item("lap_buttons_group", show=not is_shown)
    dpg.set_item_label("laps_toggle", "Laps >" if not is_shown else "Laps <")


def build_lap_buttons():
    dpg.delete_item("lap_buttons_inner", children_only=True)

    with dpg.group(horizontal=True, parent="lap_buttons_inner"):
        for entry in lap_timestamps:
            lap_num = entry["lap"]
            lap_time = entry["time"]

            if lap_time is None:
                continue

            dpg.add_button(
                label=f" {lap_num} ",
                callback=lambda s, a, u: jump_to_time(u),
                user_data=float(lap_time),
                width=38
            )


def run():
    dpg.create_context()
    dpg.create_viewport(title="F1 Track Map", width=CANVAS_WIDTH + 200, height=CANVAS_HEIGHT + 180)

    with dpg.window(label="F1 Dashboard", width=CANVAS_WIDTH + 200, height=CANVAS_HEIGHT + 180, no_resize=True, tag="main_window"):

        # Session controls
        with dpg.group(horizontal=True):
            dpg.add_input_int(label="Year", tag="year_input", default_value=2023, width=100)
            dpg.add_input_text(label="Grand Prix", tag="gp_input", default_value="Monza", width=150)
            dpg.add_input_text(label="Session", tag="session_input", default_value="R", width=60)
            dpg.add_button(label="Load Session", callback=on_load_session)

        dpg.add_text("No session loaded", tag="status_text", color=(180, 180, 180))

        # Playback controls
        with dpg.group(horizontal=True):
            dpg.add_button(label="Play", tag="play_button", callback=on_play_pause)
            dpg.add_slider_float(
                label="",
                tag="time_slider",
                min_value=0.0,
                max_value=1.0,
                callback=on_time_change,
                width=600
            )
            dpg.add_text("0:00", tag="time_display")


        with dpg.group(horizontal=True):
            dpg.add_button(label="Laps >", tag="laps_toggle", callback=on_toggle_laps)
            with dpg.group(tag="lap_buttons_group", show=False):
                with dpg.child_window(height=50, width=500, 
                        horizontal_scrollbar=True,
                        no_scrollbar=False,
                        border=False,
                        tag="lap_buttons_inner"):
                    pass

        # Speed control
        with dpg.group(horizontal=True):
            dpg.add_text("Playback Speed:")
            dpg.add_slider_float(
                label="Speed",
                tag="speed_slider",
                min_value=0.5,
                max_value=10.0,
                default_value=1.0,
                callback=lambda s, a: globals().__setitem__("animation_speed", a),
                width=300
            )


        # Drawing canvas
        with dpg.drawlist(width=CANVAS_WIDTH, height=CANVAS_HEIGHT):
            with dpg.draw_layer(tag="track_layer"):
                pass
            with dpg.draw_layer(tag="driver_layer"):
                pass



    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)

    while dpg.is_dearpygui_running():
        animation_loop()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


