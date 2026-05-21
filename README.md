# PinScope UI

A desktop GUI for designing, previewing, and deploying 8×8 pin-array configurations to physical hardware. Built with PySide6 and pyqtgraph.

## What It Does

PinScope UI lets you visually configure an 8×8 grid of motorized pins, where each pin has an independent height (0–200mm) and RGB LED color. The app provides:

- **2D grid editor** — click or drag to select pins; the inspector updates their height and color in real time
- **3D preview** — a live OpenGL rendering of the pin layout as extruded 40×40mm boxes with correct physical scale
- **Globals panel** — configure motor ramp speed and push/pull gesture behavior per board
- **File I/O** — save and load designs as `.pinscope.json` with schema validation and a recent-files list
- **TCP deploy** — connect to the Master board and send the full design (heights + LED colors + speed + gesture config) in one click

## Hardware

The physical installation is an 8×8 grid of motorized pins (40×40mm each, max height 200mm) with embedded RGB LED strips inside white PLA bodies. 8 slave boards control the motors via CAN bus, managed by a Master board over TCP.

**Module layout:** 8 modules arranged in a 4-row × 2-column grid. Each module controls a 4×2 block of pins.

**Default connection:** `192.168.0.10:5000`

## Project Structure

```
PinScopeUI/
├── pinscope/                   # Installable Python package
│   ├── pyproject.toml
│   ├── pinscope/               # Source code
│   │   ├── main.py             # Entry point
│   │   ├── __main__.py         # Enables python -m pinscope
│   │   ├── app_state.py        # Central state (Qt signals)
│   │   ├── model/
│   │   │   ├── pin.py          # Pin dataclass (height 0–200mm, r, g, b)
│   │   │   ├── design.py       # Design dataclass (64 pins + globals)
│   │   │   └── gesture.py      # GestureConfig dataclass (push/pull)
│   │   ├── io/
│   │   │   ├── design_io.py    # JSON save/load with validation
│   │   │   └── tcp_client.py   # QTcpSocket wrapper with status signals
│   │   ├── protocol/
│   │   │   └── commands.py     # Serialize Design → hardware JSON commands
│   │   └── ui/
│   │       ├── main_window.py  # Window, menus, dock layout
│   │       ├── grid_2d.py      # Interactive 8×8 grid (QGraphicsView)
│   │       ├── view_3d.py      # 3D pin preview (GLViewWidget)
│   │       ├── inspector.py    # Height slider + color picker
│   │       ├── globals_panel.py    # Motor speed + gesture config
│   │       └── connection_panel.py # Host/port, connect, deploy
│   └── tests/
│       └── test_design.py
├── design/                     # Sample .pinscope.json files
├── PinScope_SPEC.md            # Full technical specification
└── Pin_control_manual.md       # Hardware protocol reference
```

## Tech Stack

| Layer | Library |
|-------|---------|
| UI framework | PySide6 6.5+ (Qt for Python) |
| 3D graphics | pyqtgraph 0.13.3+ / PyOpenGL 3.1.7+ |
| Array ops | NumPy 1.26+ |
| Build | Hatchling |
| Lint / format | Ruff + Black (88-char lines) |
| Tests | Pytest 8.0+ |

Requires **Python 3.11+**.

## Installation

```bash
cd pinscope
pip install -e ".[dev]"
```

Or with conda (recommended):

```bash
conda activate figure
cd pinscope
pip install -e ".[dev]"
pip install PyOpenGL PyOpenGL_accelerate
```

## Running

```bash
conda activate figure
cd pinscope
python -m pinscope
```

## Deploying to Hardware

1. Ensure your machine is on the same network as the Master board (`192.168.0.x`)
2. Open the app and design your pin layout
3. In the connection bar at the bottom, click **Connect** — the status dot turns green when connected
4. Click **Deploy** to send the full design to all 8 boards

The deploy sends 74 messages total: 64 LED color commands (s:9), 8 height commands (s:1), 1 motor speed command (s:5), and 1 gesture config command (s:8).

## Design File Format

Designs are stored as `.pinscope.json`:

```json
{
  "schema_version": 1,
  "name": "My Design",
  "grid_size": [8, 8],
  "pins": [
    { "height": 100, "r": 255, "g": 255, "b": 255 },
    ...
  ],
  "motor_start_speed": 500,
  "motor_end_speed": 200,
  "global_brightness": 200,
  "push_config": { "direction": 1, "step_height": 50, "r": 255, "g": 255, "b": 255 },
  "pull_config": { "direction": 0, "step_height": 50, "r": 0, "g": 128, "b": 255 }
}
```

Pins are in row-major order: index 0 is top-left, index 63 is bottom-right.

## Architecture

State flows through a central `AppState` singleton (`QObject`) that holds the active `Design` and current selection. All UI panels communicate via Qt signals — no panel calls another directly.

```
AppState
  ├── design_changed   →  Grid2D, View3D, GlobalsPanel
  ├── pin_changed      →  Grid2D, View3D, Inspector
  ├── selection_changed → Inspector
  └── globals_changed  →  GlobalsPanel
```

Mutations only happen through `AppState` methods: `set_pin()`, `set_pins()`, `set_selection()`, `set_motor_speed()`, `set_push_config()`, `set_pull_config()`.

## Development Status

| Milestone | Status |
|-----------|--------|
| M1 – Project skeleton | Done |
| M2 – 2D grid + 3D preview | Done |
| M3 – Selection, inspector, file I/O | Done |
| M4 – Menu system + recent files | Done |
| M5 – Globals panel (motor speed, gesture config) | Done |
| M6 – TCP connection + deploy | Done |
| M5 – Library/design browser panel | Planned |
| M7 – Packaging + polish | Planned |

## Running Tests

```bash
cd pinscope
pytest
```
