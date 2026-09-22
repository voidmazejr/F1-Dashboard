import fastf1
import numpy as np
import pandas as pd
from fastf1.core import Session
import logging
import os
import pickle


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


def precompute_frames(session: Session) -> dict:
    import pickle
    import os

    FPS = 25
    DT = 1.0 / FPS

    # Check cache first
    event_name = str(session).replace(" ", "_").replace("/", "_")
    cache_path = f"cache/computed/{event_name}_frames.pkl"

    if os.path.exists(cache_path):
        print(f"Loading precomputed frames from cache...")
        with open(cache_path, "rb") as f:
            return pickle.load(f)

    drivers = session.drivers
    driver_data = {}
    global_t_min = None
    global_t_max = None

    print("Precomputing telemetry for all drivers...")

    for driver in drivers:
        try:
            driver_laps = session.laps.pick_drivers(driver)
            driver_info = session.get_driver(driver)
            code = driver_info["Abbreviation"]

            t_all = []
            x_all = []
            y_all = []
            dist_all = []
            lap_all = []
            compound_all = []

            cumulative_dist = 0.0

            for _, lap in driver_laps.iterlaps():
                telemetry = lap.get_telemetry()

                if telemetry is None or telemetry.empty:
                    continue

                lap_number = int(lap["LapNumber"])
                compound = lap["Compound"] if pd.notna(lap["Compound"]) else "?"

                t_lap = telemetry["SessionTime"].dt.total_seconds().to_numpy()
                x_lap = telemetry["X"].to_numpy()
                y_lap = telemetry["Y"].to_numpy()
                d_lap = telemetry["Distance"].to_numpy()

                race_dist = cumulative_dist + d_lap

                t_all.append(t_lap)
                x_all.append(x_lap)
                y_all.append(y_lap)
                dist_all.append(race_dist)
                lap_all.append(np.full_like(t_lap, lap_number, dtype=float))
                compound_all.append(np.full(len(t_lap), compound))

                lap_dist = telemetry["Distance"].max()
                if pd.notna(lap_dist):
                    cumulative_dist += lap_dist

            if not t_all:
                continue

            t_arr = np.concatenate(t_all)
            x_arr = np.concatenate(x_all)
            y_arr = np.concatenate(y_all)
            dist_arr = np.concatenate(dist_all)
            lap_arr = np.concatenate(lap_all)
            compound_arr = np.concatenate(compound_all)

            order = np.argsort(t_arr)
            t_arr = t_arr[order]
            x_arr = x_arr[order]
            y_arr = y_arr[order]
            dist_arr = dist_arr[order]
            lap_arr = lap_arr[order]
            compound_arr = compound_arr[order]

            t_min = t_arr.min()
            t_max = t_arr.max()

            global_t_min = t_min if global_t_min is None else min(global_t_min, t_min)
            global_t_max = t_max if global_t_max is None else max(global_t_max, t_max)

            driver_data[code] = {
                "t": t_arr,
                "x": x_arr,
                "y": y_arr,
                "dist": dist_arr,
                "lap": lap_arr,
                "compound": compound_arr,
                "team": driver_info["TeamName"],
            }

            print(f"  {code}: {len(t_arr)} telemetry points")

        except Exception as e:
            print(f"Driver {driver} error: {e}")
            continue

    if global_t_min is None or global_t_max is None:
        raise ValueError("No valid telemetry data found")

    # Build common timeline at 25fps
    timeline = np.arange(global_t_min, global_t_max, DT)
    print(f"Building {len(timeline)} frames at {FPS}fps...")

    # Resample each driver onto the common timeline
    resampled = {}
    for code, data in driver_data.items():
        t = data["t"]
        order = np.argsort(t)
        t_s = t[order]

        resampled[code] = {
            "x":        np.interp(timeline, t_s, data["x"][order]),
            "y":        np.interp(timeline, t_s, data["y"][order]),
            "dist":     np.interp(timeline, t_s, data["dist"][order]),
            "lap":      np.interp(timeline, t_s, data["lap"][order]),
            "team":     data["team"],
            "compound": data["compound"],
            "t":        data["t"],
        }

    # Build frames
    frames = []
    codes = list(resampled.keys())

    for i, t in enumerate(timeline):
        snapshot = []
        for code in codes:
            d = resampled[code]
            lap_idx = min(int(np.searchsorted(d["t"], t)), len(d["compound"]) - 1)
            snapshot.append({
                "driver": code,
                "team":   d["team"],
                "x":      float(d["x"][i]),
                "y":      float(d["y"][i]),
                "dist":   float(d["dist"][i]),
                "lap":    int(round(d["lap"][i])),
                "compound": str(d["compound"][lap_idx]),
            })

        # Sort by (lap, dist) descending
        snapshot.sort(key=lambda r: (r["lap"], r["dist"]), reverse=True)

        # Assign positions
        for pos, car in enumerate(snapshot, start=1):
            car["position"] = pos

        frames.append({
            "t": float(t),
            "drivers": snapshot,
        })

    print(f"Done. {len(frames)} frames precomputed.")

    # Save to cache
    os.makedirs("cache/computed", exist_ok=True)
    result = {
        "frames": frames,
        "t_min": float(global_t_min),  # type: ignore
        "t_max": float(global_t_max),  # type: ignore
        "fps": FPS,
    }
    with open(cache_path, "wb") as f:
        pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"Saved to cache: {cache_path}")

    return result