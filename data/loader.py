import fastf1
import numpy as np
import pandas as pd
from fastf1.core import Session
import logging

logging.getLogger("fastf1").setLevel(logging.ERROR)

fastf1.Cache.enable_cache("cache/")



def load_session(year: int, grand_prix: str, session_type: str = "R"):
    session = fastf1.get_session(year, grand_prix, session_type)
    session.load(telemetry=True, laps=True, weather=True, messages=True)

    return session


def get_track_outline(session: Session):
    lap = session.laps.pick_fastest()
    if lap is None:
        raise ValueError("No fastest lap found in this session")
    pos = lap.get_pos_data()
    circuit_info = session.get_circuit_info()
    return np.array(pos["X"]), np.array(pos["Y"]), circuit_info


def get_all_driver_positions(session: Session) -> dict:
    all_positions = {}

    for driver in session.drivers:
        try:
            driver_laps = session.laps.pick_drivers(driver)
            driver_info = session.get_driver(driver)
            frames = []
            cumulative_distance = 0.0

            for _, lap in driver_laps.iterlaps():
                telemetry = lap.get_telemetry()

                if telemetry is None or telemetry.empty:
                    continue

                for _, row in telemetry.iterrows():
                    x, y = row["X"], row["Y"]
                    if x == 0 and y == 0:
                        continue

                    frames.append({
                        "time": row["SessionTime"].total_seconds(),
                        "x": x,
                        "y": y,
                        "distance": cumulative_distance + row["Distance"],
                    })

                lap_dist = telemetry["Distance"].max()
                if pd.notna(lap_dist):
                    cumulative_distance += lap_dist

            frames.sort(key=lambda f: f["time"])

            all_positions[driver] = {
                "abbreviation": driver_info["Abbreviation"],
                "team": driver_info["TeamName"],
                "frames": frames,
                "times": np.array([f["time"] for f in frames]),
                "distances": np.array([f["distance"] for f in frames]),
            }

        except Exception as e:
            print(f"Driver {driver} error: {e}")
            continue

    return all_positions


def get_race_start_time(session: Session) -> float:
    try:
        first_laps = session.laps[session.laps["LapNumber"] == 1]
        start = first_laps["LapStartTime"].dropna().min().total_seconds()
        return float(start)
    except Exception as e:
        print(f"get_race_start_time error: {e}")
        return 0.0


def get_lap_timestamps(session: Session) -> list:
    try:
        laps = session.laps
        lap_numbers = sorted(laps["LapNumber"].unique())
        timestamps = []

        for lap_num in lap_numbers:
            lap_data = laps[laps["LapNumber"] == lap_num]
            start_time = lap_data["LapStartTime"].dropna().min()

            if pd.isna(start_time):
                continue

            timestamps.append({
                "lap": int(lap_num),
                "time": float(start_time.total_seconds())
            })

        return timestamps
    except Exception as e:
        print(f"get_lap_timestamps error: {e}")
        return []


def get_year_schedule(year: int):
    schedule = fastf1.get_event_schedule(year)
    races = schedule[schedule["EventFormat"] != "Testing"]
    return races["EventName"].tolist()


def get_event_sessions(year: int, event_name: str) -> list:
    event = fastf1.get_event(year, event_name)
    sessions = []

    session_map = {
        "Practice 1": "FP1",
        "Practice 2": "FP2",
        "Practice 3": "FP3",
        "Qualifying": "Q",
        "Sprint": "S",
        "Sprint Shootout": "SS",
        "Sprint Qualifying": "SQ",
        "Race": "R"
    }

    for i in range(1, 6):
        session_name = event.get(f"Session{i}")
        if pd.notna(session_name) and session_name in session_map:
            sessions.append({
                "label": session_name,
                "identifier": session_map[session_name]
            })
    return sessions
    

def get_race_state_at_time(session: Session, current_time: float, race_start_time: float) -> list:
    try:
        results = []

        for driver in session.drivers:
            try:
                driver_laps = session.laps.pick_drivers(driver)
                driver_info = session.get_driver(driver)

                # Find the most recent completed lap at current_time
                completed_laps = driver_laps[
                    driver_laps["LapStartTime"].dt.total_seconds() <= current_time
                ].dropna(subset=["LapStartTime"])


                if completed_laps.empty:        
                    continue

                latest_lap = completed_laps.iloc[-1]

                position = latest_lap["Position"]
                compound = latest_lap["Compound"]
                lap_number = int(latest_lap["LapNumber"])

                results.append({
                    "driver": driver_info["Abbreviation"],
                    "team": driver_info["TeamName"],
                    "position": int(position) if pd.notna(position) else 99,
                    "compound": compound if pd.notna(compound) else "?",
                    "lap_number": lap_number,
                    "lap_start_time": latest_lap["LapStartTime"].total_seconds(),
                })

            except Exception:
                continue

        # Sort by position  
        results.sort(key=lambda x: x["position"])

    
        # Sort by position
        results.sort(key=lambda x: x["position"])

        # Set placeholder gap — real gaps calculated in calculate_realtime_gaps
        for r in results:
            r["gap"] = "..."

        return results

    except Exception as e:
        print(f"get_race_state_at_time error: {e}")
        return []
