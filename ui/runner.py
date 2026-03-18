import dearpygui.dearpygui as dpg
import ui.state as state
import threading

from data.loader import (
    load_session,
    get_track_outline,
    get_all_driver_positions,
    get_race_start_time,
    get_lap_timestamps,
    get_event_sessions,
    get_year_schedule,
    get_race_state_at_time
)

from ui.drawing import (draw_track, 
                        create_driver_markers, 
                        update_driver_positions,
                        update_position_table
)

from ui.callbacks import (animation_loop, 
                          on_play_pause, 
                          on_time_change, 
                          on_toggle_laps, 
                          build_lap_buttons,
                          on_year_change,
                          on_race_change,
                          on_session_change,
                          pos_worker
)


def on_load_session(sender, app_data):
    if not state.selected_event or not state.selected_session:
        dpg.set_value("status_text", "Please select a year, race and session first")
        return
    
    sessions = get_event_sessions(state.selected_year, state.selected_event)
    session_id = next((s["identifier"] for s in sessions if s["label"] == state.selected_session), None)

    if session_id is None:
        dpg.set_value("status_text", "Error: Could not resolve session ID")
        return

    try:
        dpg.set_value("status_text", "Loading session...")

        state.session = load_session(state.selected_year, state.selected_event, session_id)

        if state.session is None:
            dpg.set_value("status_text", "Error: Could not load session")
            return

        state.track_x, state.track_y, state.circuit_info = get_track_outline(state.session)
        state.all_positions = get_all_driver_positions(state.session)
        state.race_start_time = get_race_start_time(state.session)
        state.current_time = state.race_start_time
        state.lap_timestamps = get_lap_timestamps(state.session)

        state.max_time = max(
            f["time"]
            for driver_data in state.all_positions.values()
            for f in driver_data["frames"]
        )

        dpg.configure_item("time_slider", min_value=0.0)
        dpg.configure_item("time_slider", max_value=float(state.max_time - state.race_start_time))
        dpg.set_value("status_text", f"Loaded: {state.selected_event} {state.selected_year}")

        draw_track()
        create_driver_markers()
        update_driver_positions(state.current_time)
        build_lap_buttons()
        state.race_state = get_race_state_at_time(state.session, state.current_time, state.race_start_time)
        update_position_table()

    except Exception as e:
        dpg.set_value("status_text", f"Error: {str(e)}")


def run():

    dpg.create_context()
    dpg.create_viewport(title="F1 Dashboard", width=state.CANVAS_WIDTH + 380, height=state.CANVAS_HEIGHT + 180)

    with dpg.window(label="F1 Dashboard", width=state.CANVAS_WIDTH + 380, height=state.CANVAS_HEIGHT + 180, no_resize=True, tag="main_window"):


        # Session Controls
        with dpg.group(horizontal=True):
            dpg.add_combo(
                label="Year",
                tag="year_dropdown",
                items=[str(y) for y in range(2018, 2025)],
                default_value="2023",
                callback=on_year_change,
                width=80
            )
            dpg.add_combo(
                label="Race",
                tag="race_dropdown",
                items=[],
                callback=on_race_change,
                width=200
            )
            dpg.add_combo(
                label="Session",
                tag="session_dropdown",
                items=[],
                callback=on_session_change,
                width=130
            )
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

        # Laps toggle
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
                callback=lambda s, a: setattr(state, "animation_speed", a),
                width=300
            )

        # Position panel + track map side by side
        with dpg.group(horizontal=True):

            # Left panel — position table
            with dpg.child_window(width=180, height=state.CANVAS_HEIGHT, border=True, tag="position_panel"):
                dpg.add_text("  P  Driver  T  Gap", color=(180, 180, 180, 255))
                dpg.add_separator()
                with dpg.group(tag="position_table"):
                    pass

            # Right — track map
            with dpg.drawlist(width=state.CANVAS_WIDTH, height=state.CANVAS_HEIGHT):
                with dpg.draw_layer(tag="track_layer"):
                    pass
                with dpg.draw_layer(tag="driver_layer"):
                    pass

    # Pre-populate race dropdown with default year
    try:
        races = get_year_schedule(2023)
        dpg.configure_item("race_dropdown", items=races)
    except Exception as e:
        print(f"Failed to pre-populate schedule: {e}")

    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main_window", True)


    worker = threading.Thread(target=pos_worker, daemon=True)
    worker.start()

    while dpg.is_dearpygui_running():
        animation_loop()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


