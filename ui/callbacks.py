import dearpygui.dearpygui as dpg
import ui.globals as globals
from ui.helpers import format_race_time
from ui.drawing import update_driver_positions
import time


def on_play_pause(sender, app_data):
    globals.is_playing = not globals.is_playing
    dpg.set_value("play_button", "Pause" if globals.is_playing else "Play")


def on_time_change(sender, app_data):
    globals.current_time = float(app_data) + globals.race_start_time
    dpg.set_value("time_display", format_race_time(float(app_data)))
    update_driver_positions(globals.current_time)


def jump_to_time(absolute_time: float):
    globals.current_time = absolute_time
    relative = absolute_time - globals.race_start_time
    dpg.set_value("time_slider", relative)
    dpg.set_value("time_display", format_race_time(relative))
    update_driver_positions(globals.current_time)


def on_toggle_laps(sender, app_data):
    config = dpg.get_item_configuration("lap_buttons_group")
    is_shown = config["show"]
    dpg.configure_item("lap_buttons_group", show=not is_shown)
    dpg.set_item_label("laps_toggle", "Laps >" if not is_shown else "Laps <")


def build_lap_buttons():
    dpg.delete_item("lap_buttons_inner", children_only=True)

    with dpg.group(horizontal=True, parent="lap_buttons_inner"):
        for entry in globals.lap_timestamps:
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


def animation_loop():
    if globals.max_time == 0.0 or globals.current_time == 0.0:
        return
    if not globals.is_playing:
        globals.last_frame_time = 0.0
        return
    if globals.current_time >= globals.max_time:
        globals.is_playing = False
        dpg.set_value("play_button", "Play")
        return

    now = time.time()
    if globals.last_frame_time == 0.0:
        globals.last_frame_time = now

    delta = now - globals.last_frame_time
    globals.last_frame_time = now

    globals.current_time += delta * globals.animation_speed
    dpg.set_value("time_slider", globals.current_time - globals.race_start_time)
    dpg.set_value("time_display", format_race_time(globals.current_time - globals.race_start_time))
    update_driver_positions(globals.current_time)