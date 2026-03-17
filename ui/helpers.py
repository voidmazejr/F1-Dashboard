import numpy as np
import ui.globals as globals
import dearpygui.dearpygui as dpg



def get_pos_at_time(all_positions: dict, current_time: float) -> list:
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


def format_race_time(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def normalize_coordinates(values, target_min: float, target_max: float, padding: float = 40):
    if values is None or len(values) == 0:
        return np.array([])
    min_val = values.min()
    max_val = values.max()
    scaled = ((target_max - target_min - padding * 2) / (max_val - min_val)) * (values - min_val) + target_min + padding
    return scaled


