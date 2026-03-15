# F1 Dashboard 🏎️

A Python desktop app for visualizing Formula 1 telemetry data — track maps, driver positions, lap times, weather, and more.

Built with [FastF1](https://github.com/theOehrly/Fast-F1) and [Dear PyGui](https://github.com/hoffstadt/DearPyGui).

## Features
- Interactive track map with driver positions per lap
- Lap time comparison
- Weather data (air temp, track temp, rainfall)
- Works with all F1 sessions from 2023 and back

## Setup
```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/f1-dashboard.git
cd f1-dashboard

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## Usage
1. Enter a year (e.g. `2023`), race name (e.g. `Monza`), and session type (`R` for Race, `Q` for Qualifying)
2. Click **Load Session** — first load fetches and caches data, subsequent loads are instant
3. Use the lap slider to scrub through the race

## Roadmap
- [x] Track map with driver positions
- [ ] Lap time chart
- [ ] Weather panel
- [ ] Tyre strategy view
- [ ] Live data support (OpenF1)
