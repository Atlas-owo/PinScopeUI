# PinScope Control Panel — Implementation Spec

A cross-platform (macOS + Windows) desktop application for designing, visualizing, and deploying static frames to an 8×8 pin array with RGB color and height control. Communicates with the hardware over TCP/IP.

---

## 1. Goals

- Provide a polished, demo-ready interface for the MIT PIN project.
- Let the user create, edit, save, load, and deploy **designs** — full 8×8 pin states (height + RGB per pin) plus global parameters.
- Offer both a **2D top-down editor** (primary editing surface) and a **3D preview** with optional glow.
- Send designs to hardware over TCP/IP via a defined wire protocol.

Non-goals for v1: animations, multi-user collaboration, undo/redo across sessions, network discovery.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11+ | |
| UI framework | **PySide6** | LGPL, official Qt-for-Python |
| 3D view | **pyqtgraph** (`GLViewWidget`) | Embeds in PySide6, sufficient for 64 pins |
| OpenGL | PyOpenGL | pyqtgraph dependency |
| Array math | NumPy | pyqtgraph dependency, also used internally |
| TCP client | `QTcpSocket` | Integrates with Qt event loop |
| Persistence | JSON (stdlib) | designs saved as `.pinscope.json` files |
| Settings | `QSettings` | window geometry, last host/port, recent files |
| Packaging | PyInstaller | unsigned `.app` and `.exe` |
| Dependency mgmt | `uv` (preferred) or `poetry` | reproducible env |

---

## 3. Data Model

### 3.1 Pin

```python
@dataclass
class Pin:
    height: int  # 0–255
    r: int       # 0–255
    g: int       # 0–255
    b: int       # 0–255
```

### 3.2 Design

```python
@dataclass
class Design:
    name: str
    pins: list[Pin]              # length 64, row-major (row 0 = top, col 0 = left)
    motor_speed: int             # 0–255 (placeholder; adjust to hardware range)
    global_brightness: int       # 0–255
    # Forward-compatibility: animation fields reserved but unused in v1.
    # When animations are added: introduce `frames: list[Frame]` and treat
    # the current `pins` field as frame 0 for backward compatibility.
    schema_version: int = 1
```

### 3.3 JSON file format (`.pinscope.json`)

```json
{
  "schema_version": 1,
  "name": "Wave Pattern",
  "grid_size": [8, 8],
  "pins": [
    {"height": 120, "r": 255, "g": 80, "b": 0},
    ...64 entries total, row-major...
  ],
  "motor_speed": 128,
  "global_brightness": 200
}
```

`grid_size` is stored explicitly so future versions can support other dimensions without breaking old files. v1 readers reject anything other than `[8, 8]`.

---

## 4. Application Architecture

### 4.1 Project layout

```
pinscope/
├── pyproject.toml
├── README.md
├── pinscope/
│   ├── __init__.py
│   ├── main.py                  # QApplication entry point
│   ├── app_state.py             # singleton-ish AppState holding the current Design
│   ├── model/
│   │   ├── __init__.py
│   │   ├── pin.py
│   │   └── design.py
│   ├── io/
│   │   ├── __init__.py
│   │   ├── design_io.py         # JSON load/save, schema validation
│   │   └── tcp_client.py        # QTcpSocket wrapper
│   ├── protocol/
│   │   ├── __init__.py
│   │   └── commands.py          # serialize Design -> wire bytes (see §6)
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   ├── grid_2d.py           # 8×8 interactive grid (QGraphicsView)
│   │   ├── view_3d.py           # pyqtgraph GLViewWidget wrapper
│   │   ├── inspector.py         # height slider + color picker for selection
│   │   ├── globals_panel.py     # motor speed, global brightness, etc.
│   │   ├── library_panel.py     # recent/saved designs
│   │   ├── connection_panel.py  # host/port, connect, status indicator
│   │   └── styles.py            # Qt stylesheet for polished look
│   └── resources/
│       ├── icons/
│       └── app.qss              # optional stylesheet
└── tests/
    ├── test_design.py
    ├── test_design_io.py
    └── test_commands.py
```

### 4.2 State flow

- A single `AppState` holds the current `Design` and a list of selected pin indices.
- `AppState` emits Qt signals (`design_changed`, `selection_changed`, `pin_changed(index)`) that all views subscribe to.
- Edits never bypass `AppState` — both the 2D grid and the inspector mutate it through methods like `set_pin(i, pin)` or `set_pins(indices, pin)`, which then emit the appropriate signal.
- This keeps 2D, 3D, and inspector views automatically in sync.

### 4.3 Live vs. Deploy mode

- Toolbar toggle: **Deploy** (manual button) vs **Live** (auto-send on every `design_changed`).
- In Live mode, debounce sends to ~30 Hz max to avoid flooding the socket.

---

## 5. UI Layout

Main window structure:

```
┌─────────────────────────────────────────────────────────────┐
│  File   Edit   View   Deploy   Help              [● Connected] │  ← menu + status
├──────────────┬──────────────────────────────┬───────────────┤
│              │                              │               │
│  Library     │      2D Grid (primary)       │   Inspector   │
│  panel       │      ┌─┬─┬─┬─┬─┬─┬─┬─┐       │   ┌─────────┐ │
│  (dock)      │      │ │ │ │ │ │ │ │ │       │   │ Color   │ │
│              │      ├─┼─┼─┼─┼─┼─┼─┼─┤       │   │ picker  │ │
│              │      │ │ │ │ │ │ │ │ │       │   └─────────┘ │
│              │      ...                     │   Height: ▭▭▭ │
│              │                              │               │
│              ├──────────────────────────────┤   Globals     │
│              │      3D Preview              │   Motor: ▭▭   │
│              │                              │   Bright: ▭▭  │
│              │                              │               │
├──────────────┴──────────────────────────────┴───────────────┤
│  Connection: [host____] [port__] [Connect] [Deploy] [Live☐] │
└─────────────────────────────────────────────────────────────┘
```

All side panels are `QDockWidget`s so the user can rearrange or hide them.

### 5.1 2D grid (primary editor)

- 8×8 grid of cells in a `QGraphicsView`.
- Each cell shows: fill color = pin RGB; height indicated by a vertical bar overlay or numeric label (toggle in View menu).
- Click to select; Shift/Cmd-click to extend; drag to box-select; Cmd/Ctrl+A selects all.
- Selected cells get a high-contrast outline.
- Drag-paint mode (toolbar toggle): clicking and dragging applies current inspector color/height.

### 5.2 3D view

- `pyqtgraph.opengl.GLViewWidget` showing 64 cylinders on a dark base plate.
- Cylinder height proportional to `pin.height` (scale factor configurable).
- Cylinder color = pin RGB; use `shader='shaded'` for basic directional lighting.
- **Glow effect (toggle):** for each pin, draw a larger semi-transparent cylinder around it with `GLOptions='additive'`. Optionally a second even-larger, even-more-transparent shell.
- Orbit/pan/zoom via mouse (pyqtgraph default).
- Reset-camera button in toolbar.

### 5.3 Inspector

- Color picker (`QColorDialog` embedded or a `QColorPicker`-style widget).
- Height slider 0–255 with numeric spinbox.
- "Apply to selection" is implicit — changes apply live to all selected pins.
- "Copy" / "Paste" pin state buttons.

### 5.4 Globals panel

- Motor speed: slider 0–255 + spinbox.
- Global brightness: slider 0–255 + spinbox.
- Easy to add more sliders here later.

### 5.5 Library panel

- List of recent and saved designs (from a designated directory under user data, e.g. `~/Documents/PinScope/`).
- Double-click to load; right-click for rename/duplicate/delete.
- "+ New" button at top.

### 5.6 Connection panel

- Host (text), port (spinbox), Connect / Disconnect button.
- Status indicator: gray (disconnected) / yellow (connecting) / green (connected) / red (error).
- Deploy button (sends current design once).
- Live toggle.

---

## 6. TCP Protocol

> **TODO (Ilan to fill in):** Paste the defined hardware protocol here. The `protocol/commands.py` module should expose at minimum:
>
> ```python
> def serialize_frame(design: Design) -> bytes: ...
> def serialize_motor_speed(value: int) -> bytes: ...
> def serialize_brightness(value: int) -> bytes: ...
> ```
>
> The TCP client in `io/tcp_client.py` calls these and writes the bytes to the socket. Until the protocol is filled in, use a stub that prints the bytes to stdout so the rest of the UI can be developed and tested.

---

## 7. File I/O

- **Open / Save / Save As** under the File menu, standard shortcuts (Cmd/Ctrl+O, S, Shift+S).
- File extension: `.pinscope.json`.
- On load: validate `schema_version == 1` and `grid_size == [8, 8]`; show a friendly error dialog on mismatch.
- On save: pretty-printed JSON with 2-space indent.
- "Recent Files" submenu under File, backed by `QSettings`.

---

## 8. Settings & Persistence

Stored via `QSettings`:

- Window geometry and dock layout
- Last-used TCP host/port
- Recent files (max 10)
- View preferences (glow on/off, height display mode, etc.)

---

## 9. Milestones & Acceptance Criteria

Each milestone is independently runnable and reviewable. Claude Code should complete them in order.

### M1 — Project skeleton & 2D grid render

- `pyproject.toml` with PySide6, pyqtgraph, numpy.
- `main.py` launches a main window with menu bar.
- `Design` and `Pin` dataclasses implemented with sensible defaults (all pins height=0, color=black).
- `AppState` with signals.
- 2D grid renders 8×8 colored squares from the current design (no interactivity yet).
- **Acceptance:** Running `python -m pinscope` opens a window showing an 8×8 grid of black squares on both macOS and Windows.

### M2 — Selection & inspector

- Click / shift-click / drag selection in 2D grid.
- Inspector panel with color picker and height slider, bound to selection.
- Edits propagate through `AppState` and update the grid live.
- **Acceptance:** User can select one or many pins and change their color and height; grid updates immediately.

### M3 — JSON I/O

- `design_io.py` with `load(path)` and `save(path, design)`.
- File menu wired to Open / Save / Save As / Recent Files.
- Schema validation with friendly error dialogs.
- **Acceptance:** Round-trip: edit a design, save, close app, reopen, load — state matches.

### M4 — 3D preview

- `view_3d.py` with `GLViewWidget`, cylinders for each pin, base plate.
- Live updates from `AppState`.
- Glow toggle in View menu.
- Reset camera button.
- **Acceptance:** 3D view updates in real time as the 2D grid is edited; glow toggle works.

### M5 — Globals & library panels

- Globals panel with motor speed and brightness sliders.
- Library panel listing designs from `~/Documents/PinScope/` (or platform equivalent).
- Double-click to load, right-click context menu.
- **Acceptance:** Designs saved to the library directory appear in the panel and load on double-click.

### M6 — TCP client & deploy

- `tcp_client.py` wrapping `QTcpSocket`, exposing `connect(host, port)`, `disconnect()`, `send(bytes)`, status signal.
- Connection panel wired up.
- Deploy button sends serialized current design.
- Live toggle: debounced auto-send on `design_changed`.
- **Acceptance:** With a stub protocol that prints bytes, clicking Deploy logs the expected payload; Live mode logs payloads as edits happen, debounced to ≤30 Hz.

### M7 — Polish & packaging

- App icon, About dialog, keyboard shortcuts documented.
- Light Qt stylesheet for consistent look on both OSes.
- `QSettings`-backed geometry and recents.
- PyInstaller spec files for macOS (`.app`) and Windows (`.exe`), build instructions in README.
- **Acceptance:** Built `.app` and `.exe` launch on a clean machine and load/save/deploy designs.

---

## 10. Conventions

- **Type hints everywhere.** Use `from __future__ import annotations`.
- **Black** for formatting, **ruff** for linting (configure in `pyproject.toml`).
- **pytest** for tests. Cover the model, I/O, and protocol modules. UI tests are out of scope for v1.
- **No business logic in UI files.** UI files only handle layout, signal wiring, and user input. Mutations go through `AppState`.
- **Qt signals over callbacks** for cross-component communication.
- **No global mutable state** outside `AppState`.
- Imports ordered: stdlib → third-party → first-party.
- Docstrings on all public classes and non-trivial functions.

---

## 11. Open Questions / TODOs

- [ ] Paste TCP protocol spec into §6.
- [ ] Confirm motor speed range (0–255? 0–4095? RPM?).
- [ ] Confirm whether brightness is applied per-pin client-side before sending, or as a global parameter the hardware applies.
- [ ] Decide on physical mapping: which pin index corresponds to which physical position on the array? (Row-major from which corner?)
- [ ] App icon design.

---

## 12. Future (post-v1)

- Animations: `frames: list[Frame]` in the schema, timeline panel, playback controls, frame interpolation.
- Undo/redo history (likely `QUndoStack` per design).
- Copy/paste regions, mirror, rotate, fill tools.
- Import from image (map pixel brightness → height, color → RGB).
- Larger grid sizes (read `grid_size` from file).
- Network discovery (mDNS) for hardware.
