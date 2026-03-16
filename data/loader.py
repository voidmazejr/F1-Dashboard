import fastf1
import numpy as np
import pandas as pd
from fastf1.core import Session



fastf1.Cache.enable_cache("cache/")

def load_session(year: int, grand_prix: str, session_type: str = "R"): 
    session = fastf1.get_session(year, grand_prix, session_type)
    session.load(telemetry=True, laps=True, weather=True, messages=True)
    return session


def get_race_start_time(session: Session) -> float:
    try:
        first_laps = session.laps[session.laps["LapNumber"] == 1]
        start = first_laps["LapStartTime"].dropna().min().total_seconds()
        print(f"Race start time: {start}")
        return float(start)
    except Exception as e:
        print(f"get_race_start_time error: {e}")
        return 0.0
    

def get_track_outline(session: Session):
    lap = session.laps.pick_fastest()
    if lap is None:
        raise ValueError("No laps found for the session.")
    
    pos = lap.get_pos_data()
    circuit_info = session.get_circuit_info()
    
    return np.array(pos["X"].values), np.array(pos["Y"].values), circuit_info


def get_all_driver_positions(session: Session) -> dict:
    all_positions = {}

    for driver in session.drivers:
        try:
            driver_laps = session.laps.pick_drivers(driver)
            driver_info = session.get_driver(driver)

            frames = []
            for _, lap in driver_laps.iterlaps():
                pos_data = lap.get_pos_data()

                if pos_data is None or pos_data.empty:
                    continue

                for _, row in pos_data.iterrows():
                    x, y = row["X"], row["Y"]

                    if x == 0 and y == 0:  # skip bad GPS frames
                        continue

                    frames.append({
                        "time": row["SessionTime"].total_seconds(),
                        "x": x,
                        "y": y,
                    })

            all_positions[driver] = {
                "abbreviation": driver_info["Abbreviation"],
                "team": driver_info["TeamName"],
                "frames": sorted(frames, key=lambda f: f["time"]),
                "times": np.array(sorted([f["time"] for f in frames]))
            }

        except Exception:
            continue

    return all_positions


def get_lap_timestamps(session: Session):
    try:
        laps = session.laps
        lap_numbers = sorted(laps["LapNumber"].unique())
        timestamps = []

        for lap_num in lap_numbers:
            lap_data = laps[laps["LapNumber"] == lap_num]
            start_time = lap_data["LapStartTime"].dropna().min()

            if pd.isna(start_time):  # skip laps with no valid start time
                continue

            timestamps.append({
                "lap": int(lap_num),
                "time": float(start_time.total_seconds())
            })

        return timestamps
    except Exception as e:
        print(f"get_lap_timestamps error: {e}")
        return []
