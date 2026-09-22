import dearpygui.dearpygui as dpg
import ui.state as state
from ui.helpers import format_race_time
from ui.drawing import apply_positions, update_position_table
from data.loader import get_year_schedule, get_event_sessions
import time


def on_play_pause(sender, app_data):
    state.is_playing = not state.is_playing
    dpg.set_value("play_button", "Pause" if state.is_playing else "Play")


def on_frame_change(sender, app_data):
    state.frame_index = int(app_data)
    _render_frame(state.frame_index)


def jump_to_frame(frame_index: int):
    state.frame_index = max(0, min(frame_index, state.total_frames - 1))
    dpg.set_value("time_slider", state.frame_index)
    _render_frame(state.frame_index)


def jump_to_time(absolute_time: float):
    if not state.frames:
        return
    # Find closest frame to this absolute time
    target = absolute_time - state.t_min
    frame_idx = int(target * state.fps)
    jump_to_frame(frame_idx)


def _render_frame(frame_index: int):
    if not state.frames or frame_index >= len(state.frames):
        return

    frame = state.frames[frame_index]
    t_relative = frame["t"] - state.t_min
    dpg.set_value("time_display", format_race_time(t_relative))

    positions = [
        {
            "driver": car["driver"],
            "team": car["team"],
            "x": car["x"],
            "y": car["y"],
        }
        for car in frame["drivers"]
    ]
    apply_positions(positions)

    # Update table every 30 frames
    if frame_index % 30 == 0:
        update_position_table()


def animation_loop():
    if not state.frames:
        return

    if not state.is_playing:
        state.last_frame_time = 0.0
        return
    if state.frame_index >= state.total_frames - 1:
        state.is_playing = False
        dpg.set_value("play_button", "Play")
        return

    now = time.time()
    if state.last_frame_time == 0.0:
        state.last_frame_time = now

    delta = now - state.last_frame_time
    state.last_frame_time = now

    state.frame_accumulator += delta * state.fps * state.animation_speed


    if state.frame_accumulator >= 1.0:
        frames_to_advance = int(state.frame_accumulator)
        state.frame_accumulator -= frames_to_advance
        state.frame_index = min(
            state.frame_index + frames_to_advance,
            state.total_frames - 1
        )
        dpg.set_value("time_slider", state.frame_index)
        _render_frame(state.frame_index)


def on_toggle_laps(sender, app_data):
    config = dpg.get_item_configuration("lap_buttons_group")
    is_shown = config["show"]
    dpg.configure_item("lap_buttons_group", show=not is_shown)
    dpg.set_item_label("laps_toggle", "Laps >" if not is_shown else "Laps <")


def build_lap_buttons():
    dpg.delete_item("lap_buttons_inner", children_only=True)

    if not state.frames:
        return

    # Find the first frame for each lap number
    lap_frames = {}
    for i, frame in enumerate(state.frames):
        for car in frame["drivers"]:
            lap = car["lap"]
            if lap not in lap_frames:
                lap_frames[lap] = i
            break

    with dpg.group(horizontal=True, parent="lap_buttons_inner"):
        for lap_num in sorted(lap_frames.keys()):
            frame_idx = lap_frames[lap_num]
            dpg.add_button(
                label=f" {lap_num} ",
                callback=lambda s, a, u: jump_to_frame(u),
                user_data=frame_idx,
                width=38
            )


def on_year_change(sender, app_data):
    state.selected_year = int(app_data)
    try:
        races = get_year_schedule(state.selected_year)
        dpg.configure_item("race_dropdown", items=races)
        dpg.set_value("race_dropdown", "")
        dpg.set_value("session_dropdown", "")
        dpg.configure_item("session_dropdown", items=[])
    except Exception as e:
        print(f"on_year_change error: {e}")


def on_race_change(sender, app_data):
    state.selected_event = app_data
    try:
        sessions = get_event_sessions(state.selected_year, state.selected_event)
        session_labels = [s["label"] for s in sessions]
        dpg.configure_item("session_dropdown", items=session_labels)
        dpg.set_value("session_dropdown", "")
    except Exception as e:
        print(f"on_race_change error: {e}")


def on_session_change(sender, app_data):
    state.selected_session = app_data


def pos_worker():
    # No longer needed with precomputed frames
    # Kept to avoid import errors until fully cleaned up
    pass