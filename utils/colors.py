import fastf1.plotting
from fastf1.core import Session

def get_team_color(team: str, session: Session):
    try:
        return fastf1.plotting.get_team_color(team, session, colormap="official")
    except Exception:
        return "#FFFFFF"  # Return white if team color is not found