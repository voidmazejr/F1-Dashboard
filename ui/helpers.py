import numpy as np
import ui.state as state
import dearpygui.dearpygui as dpg


def get_pos_at_time(all_positions: dict, current_time: float) -> list:
    positions = []

    def catmull_rom(p0, p1, p2, p3, t):
        return (
            0.5 * (2 * p1
            + (-p0 + p2) * t
            + (2*p0 - 5*p1 + 4*p2 - p3) * t**2
            + (-p0 + 3*p1 - 3*p2 + p3) * t**3)
        )

    for driver_num, driver_data in all_positions.items():
        frames = driver_data["frames"]
        times = driver_data["times"]

        if len(frames) == 0:
            continue

        idx = int(np.searchsorted(times, current_time))

        if idx <= 0:
            positions.append({
                "driver": driver_data["abbreviation"],
                "team": driver_data["team"],
                "x": frames[0]["x"],
                "y": frames[0]["y"],
            })
            continue

        if idx >= len(frames):
            positions.append({
                "driver": driver_data["abbreviation"],
                "team": driver_data["team"],
                "x": frames[-1]["x"],
                "y": frames[-1]["y"],
            })
            continue

        # Get 4 surrounding frames
        i0 = max(idx - 2, 0)
        i1 = max(idx - 1, 0)
        i2 = min(idx, len(frames) - 1)
        i3 = min(idx + 1, len(frames) - 1)

        p0 = (frames[i0]["x"], frames[i0]["y"])
        p1 = (frames[i1]["x"], frames[i1]["y"])
        p2 = (frames[i2]["x"], frames[i2]["y"])
        p3 = (frames[i3]["x"], frames[i3]["y"])

        # How far between p1 and p2
        time_range = frames[i2]["time"] - frames[i1]["time"]
        if time_range == 0:
            t = 0.0
        else:
            t = (current_time - frames[i1]["time"]) / time_range
        t = max(0.0, min(1.0, t))

        x = catmull_rom(p0[0], p1[0], p2[0], p3[0], t)
        y = catmull_rom(p0[1], p1[1], p2[1], p3[1], t)

        positions.append({
            "driver": driver_data["abbreviation"],
            "team": driver_data["team"],
            "x": x,
            "y": y,
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


def calculate_realtime_gaps(all_positions: dict, current_time: float, race_state: list, lap_timestamps: list) -> dict:
    gaps = {}

    if not all_positions:
        return gaps

    # Calculate current distance for every driver
    driver_distances = {}
    for driver_num, driver_data in all_positions.items():
        times = driver_data["times"]
        dists = driver_data["distances"]
        if len(times) == 0 or len(dists) == 0:
            continue
        driver_distances[driver_num] = float(np.interp(current_time, times, dists))

    if not driver_distances:
        return gaps

    sorted_drivers = sorted(driver_distances.items(), key=lambda x: x[1], reverse=True)
    leader_num, leader_dist = sorted_drivers[0]

    # Before 1000m — use race_state positions and gaps
    if leader_dist < 1000:
        if not race_state:
            return gaps
        leader_entry = next((r for r in race_state if r["position"] == 1), None)
        if not leader_entry:
            return gaps
        gaps[leader_entry["driver"]] = "Leader"
        for entry in race_state:
            if entry["position"] == 99 or entry["driver"] == leader_entry["driver"]:
                continue
            gaps[entry["driver"]] = entry.get("gap", "—")
        return gaps

    # After 1000m — use distance-based calculation synced with visualization
    leader_data = all_positions[leader_num]
    leader_abbr = leader_data["abbreviation"]
    l_times = leader_data["times"]
    l_dists = leader_data["distances"]

    gaps[leader_abbr] = "Leader"

    for driver_num, current_dist in sorted_drivers[1:]:
        driver_data = all_positions[driver_num]
        abbr = driver_data["abbreviation"]

        time_leader_was_there = float(np.interp(current_dist, l_dists, l_times))
        gap = current_time - time_leader_was_there

        if gap > 120:
            driver_entry = next((r for r in race_state if r["driver"] == abbr), None)
            leader_entry = next((r for r in race_state if r["driver"] == leader_abbr), None)
            if driver_entry and leader_entry:
                diff = leader_entry["lap_number"] - driver_entry["lap_number"]
                gaps[abbr] = f"+{diff}L" if diff > 0 else f"+{gap:.1f}s"
            else:
                gaps[abbr] = "+1L"
        elif gap < 0:
            gaps[abbr] = "Leader"
        else:
            gaps[abbr] = f"+{gap:.1f}s"

    return gaps