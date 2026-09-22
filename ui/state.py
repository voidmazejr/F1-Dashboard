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
pit_x: Optional[np.ndarray] = None
pit_y: Optional[np.ndarray] = None
circuit_info = None

# Precomputed frames
frames: list = []
frame_index: int = 0
frame_accumulator: float = 0.0
total_frames: int = 0
fps: int = 25
t_min: float = 0.0
t_max: float = 0.0

# Position table stability
stable_positions: dict = {}
position_hold_frames: dict = {}

# Legacy
all_positions: dict = {}
lap_timestamps: list = []
race_state: list = []

# Canvas bounds cache
canvas_x_min: float = 0.0
canvas_x_max: float = 0.0
canvas_y_min: float = 0.0
canvas_y_max: float = 0.0

# Session Selection
selected_year: int = 2023
selected_event: str = ""
selected_session: str = ""

# Animation state
current_time: float = 0.0
max_time: float = 0.0
race_start_time: float = 0.0
animation_speed: float = 1.0
last_frame_time: float = 0.0
last_table_update: float = 0.0
is_playing: bool = False

# Driver markers
driver_tags: dict = {}

# Thread safety
position_buffer: list = []
buffer_lock = threading.Lock()
render_mutex = threading.Lock()