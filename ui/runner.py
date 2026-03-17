import dearpygui.dearpygui as dpg
import ui.globals as globals
from data.loader import (
    load_session,
    get_track_outline,
    get_all_driver_positions,
    get_race_start_time,
    get_lap_timestamps
)
from ui.drawing import draw_track, create_driver_markers, update_driver_positions
from ui.callbacks import animation_loop, on_play_pause, on_time_change, on_toggle_laps, build_lap_buttons


def on_load_session(sender, app_data):
    year = int(dpg.get_value("year_input"))
    grand_prix = dpg.get_value("gp_input")
    session_type = dpg.get_value("session_input")

    try:
        dpg.set_value("status_text", "Loading session...")

        globals.session = load_session(year, grand_prix, session_type)

        if globals.session is None:
            dpg.set_value("status_text", "Error: Could not load session")
            return

        globals.track_x, globals.track_y, globals.circuit_info = get_track_outline(globals.session)
        globals.all_positions = get_all_driver_positions(globals.session)
        globals.race_start_time = get_race_start_time(globals.session)
        globals.current_time = globals.race_start_time
        globals.lap_timestamps = get_lap_timestamps(globals.session)

        globals.max_time = max(
            f["time"]
            for driver_data in globals.all_positions.values()
            for f in driver_data["frames"]
        )

        dpg.configure_item("time_slider", min_value=0.0)
        dpg.configure_item("time_slider", max_value=float(globals.max_time - globals.race_start_time))
        dpg.set_value("status_text", f"Loaded: {grand_prix} {year}")

        draw_track()
        create_driver_markers()
        update_driver_positions(globals.current_time)
        build_lap_buttons()

    except Exception as e:
        dpg.set_value("status_text", f"Error: {str(e)}")


def run():
    dpg.create_context()
    dpg.create_viewport(title="F1 Dashboard", width=globals.CANVAS_WIDTH + 200, height=globals.CANVAS_HEIGHT + 180)

    with dpg.window(label="F1 Dashboard", width=globals.CANVAS_WIDTH + 200, height=globals.CANVAS_HEIGHT + 180, no_resize=True, tag="main_window"):

        with dpg.group(horizontal=True):
            dpg.add_input_int(label="Year", tag="year_input", default_value=2023, width=100)
            dpg.add_input_text(label="Grand Prix", tag="gp_input", default_value="Monza", width=150)
            dpg.add_input_text(label="Session", tag="session_input", default_value="R", width=60)
            dpg.add_button(label="Load Session", callback=on_load_session)

        dpg.add_text("No session loaded", tag="status_text", color=(180, 180, 180))

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

        with dpg.group(horizontal=True):
            dpg.add_text("Playback Speed:")
            dpg.add_slider_float(
                label="Speed",
                tag="speed_slider",
                min_value=0.5,
                max_value=10.0,
                default_value=1.0,
                callback=lambda s, a: setattr(globals, "animation_speed", a),
                width=300
            )

        with dpg.drawlist(width=globals.CANVAS_WIDTH, height=globals.CANVAS_HEIGHT):
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