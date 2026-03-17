import dearpygui.dearpygui as dpg
import ui.state as state
from ui.helpers import format_race_time, get_pos_at_time
from ui.drawing import update_driver_positions, apply_positions
from data.loader import get_year_schedule, get_event_sessions, get_all_driver_positions
import time



def on_play_pause(sender, app_data):
    state.is_playing = not state.is_playing
    dpg.set_value("play_button", "Pause" if state.is_playing else "Play")


def on_time_change(sender, app_data):
    state.current_time = float(app_data) + state.race_start_time
    dpg.set_value("time_display", format_race_time(float(app_data)))
    update_driver_positions(state.current_time)


def jump_to_time(absolute_time: float):
    state.current_time = absolute_time
    relative = absolute_time - state.race_start_time
    dpg.set_value("time_slider", relative)
    dpg.set_value("time_display", format_race_time(relative))
    update_driver_positions(state.current_time)


def on_toggle_laps(sender, app_data):
    config = dpg.get_item_configuration("lap_buttons_group")
    is_shown = config["show"]
    dpg.configure_item("lap_buttons_group", show=not is_shown)
    dpg.set_item_label("laps_toggle", "Laps >" if not is_shown else "Laps <")


def build_lap_buttons():
    dpg.delete_item("lap_buttons_inner", children_only=True)

    with dpg.group(horizontal=True, parent="lap_buttons_inner"):
        for entry in state.lap_timestamps:
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


def on_year_change(sender, app_data):
    state.selected_year = int(app_data)

    try: 
        races = get_year_schedule(state.selected_year)
        dpg.configure_item("race_dropdown", items=races)
        dpg.set_value("race_dropdown", "")
        dpg.set_value("session_dropdown", "")
        dpg.configure_item("session_dropdown", items=[])
    
    except Exception as e: 
        print(f"on_year_change() error: {e}")


def on_race_change(sender, app_data): 
    state.selected_event = app_data

    try:
        sessions = get_event_sessions(state.selected_year, state.selected_event)
        session_labels = [s["label"] for s in sessions]
        dpg.configure_item("session_dropdown", items=session_labels)
        dpg.set_value("session_dropdown", "")
    except Exception as e:
        print(f"on_race_change() error: {e}")


def on_session_change(sender, app_data): 
    state.selected_session = app_data


def pos_worker():
    while True:
        if state.is_playing:
            positions = get_pos_at_time(state.all_positions, state.current_time)
            with state.buffer_lock:
                state.position_buffer = positions
        time.sleep(0.016)


def animation_loop():
    if state.max_time == 0.0 or state.current_time == 0.0:
        return
    if not state.is_playing:
        state.last_frame_time = 0.0
        return
    if state.current_time >= state.max_time:
        state.is_playing = False
        dpg.set_value("play_button", "Play")
        return

    now = time.time()
    if state.last_frame_time == 0.0:
        state.last_frame_time = now

    delta = now - state.last_frame_time
    state.last_frame_time = now
    state.current_time += delta * state.animation_speed

    dpg.set_value("time_slider", state.current_time - state.race_start_time)
    dpg.set_value("time_display", format_race_time(state.current_time - state.race_start_time))

    with state.buffer_lock:
        positions = list(state.position_buffer)

    if positions:
        apply_positions(positions)

    # Debug FPS — remove later
    # if delta > 0 and int(state.current_time) % 2 == 0:
    #     print(f"FPS: {1/delta:.0f}")
        
