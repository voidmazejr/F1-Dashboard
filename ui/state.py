import numpy as np
from fastf1.core import Session
from typing import Optional
import threading

# Canvas dimensions
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 700

# Session state
session: Optional[Session] = None
track_x: Optional[np.ndarray] = None
track_y: Optional[np.ndarray] = None
circuit_info = None
all_positions: dict = {}
lap_timestamps: list = []


race_state: list = []
last_table_update: float = 0.0

# Thread safety
# Optimization
last_positions: dict = {}  # driver -> (px, py)
position_buffer: list = []
buffer_lock = threading.Lock()
render_mutex = threading.Lock()

# Session Selection Default Values
selected_year: int = 2023
selected_event: str = ""
selected_session: str = ""

# Animation state
current_time: float = 0.0
max_time: float = 0.0
race_start_time: float = 0.0
animation_speed: float = 1.0
last_frame_time: float = 0.0
is_playing: bool = False

# Driver markers
driver_tags: dict = {}
