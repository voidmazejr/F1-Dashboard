import fastf1.plotting
from fastf1.core import Session

def get_team_color(team: str, session: Session):
    try:
        return fastf1.plotting.get_team_color(team, session, colormap="official")
    except Exception:
        return "#FFFFFF"  # Return white if team color is not found
    

COMPOUND_COLORS = {
    "SOFT":         (255, 50,  50,  255),
    "MEDIUM":       (255, 210, 0,   255),
    "HARD":         (255, 255, 255, 255),
    "INTERMEDIATE": (50,  200, 50,  255),
    "WET":          (0,   100, 255, 255),
    "?":            (150, 150, 150, 255),
}

def get_compound_color(compound: str) -> tuple:
    return COMPOUND_COLORS.get(compound.upper(), (150, 150, 150, 255))