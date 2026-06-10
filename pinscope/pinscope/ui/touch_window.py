from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from .view_3d import View3D
from ..app_state import AppState
from ..io import design_io
from ..io.tcp_client import TcpClient
from ..model.pin import Pin
from ..protocol.commands import serialize_heights, serialize_colors

KIOSK_HOST = "192.168.0.10"
KIOSK_PORT = 5000
CYCLE_DEMO_DIR = Path(__file__).resolve().parents[3] / "presets" / "cycle_demo"
DEFAULT_CYCLE_SECONDS = 60
TRANSITION_MS = 4000   # demo-switch height animation duration
TRANSITION_STEP_MS = 16  # ~60 fps

_BG       = "#0d0d0d"
_PANEL_BG = "#101010"
_DIVIDER  = "#1a1a1a"
_ACCENT   = "#00c6a7"
_CARD_BG  = "#161616"
_TEXT     = "#dddddd"
_SUBTEXT  = "#444444"

# Gradient themes. Each theme maps pin height (0–200 mm) to a color via
# evenly-spaced RGB stops: stop[0] = height 0, stop[-1] = height 200.
# "hint" is the button accent color shown in the UI.
_THEMES: list[dict | None] = [
    None,  # original colors from file
    {
        "name": "EMBER",
        "hint": "#ff7c00",
        "stops": [
            (12,  2,  2),   # near-black ember base
            (160, 18,  4),  # deep red
            (230, 75,  0),  # orange
            (255, 200, 45), # bright gold tip
        ],
    },
    {
        "name": "OCEAN",
        "hint": "#00d4ff",
        "stops": [
            (4,   6,  30),  # deep abyss navy
            (0,  55, 160),  # ocean blue
            (0, 160, 220),  # tropical blue
            (70, 240, 255), # bright cyan surface
        ],
    },
    {
        "name": "AURORA",
        "hint": "#00ff99",
        "stops": [
            (6,   0,  22),  # deep space indigo
            (70,  0, 130),  # violet
            (0,  140, 110), # teal green
            (90, 255, 180), # bright aurora tip
        ],
    },
    {
        "name": "SUNSET",
        "hint": "#ffcc44",
        "stops": [
            (10,  4,  28),  # deep twilight purple
            (130, 18,  85), # magenta dusk
            (220, 65,  20), # orange-red horizon
            (255, 215, 70), # warm gold zenith
        ],
    },
    {
        "name": "NEON",
        "hint": "#dd00ff",
        "stops": [
            (6,   0,  14),  # near black
            (150,  0, 200), # deep violet
            (220,  0, 100), # hot pink
            (0,  240, 200), # electric cyan tip
        ],
    },
]


def _gradient_color(height: float, stops: list[tuple]) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, height / 200.0))
    n = len(stops) - 1
    scaled = t * n
    i = min(int(scaled), n - 1)
    frac = scaled - i
    r0, g0, b0 = stops[i]
    r1, g1, b1 = stops[i + 1]
    return (
        int(r0 + frac * (r1 - r0)),
        int(g0 + frac * (g1 - g0)),
        int(b0 + frac * (b1 - b0)),
    )

_CARD_INACTIVE = f"""
QPushButton {{
    background: {_CARD_BG};
    border: none;
    border-left: 3px solid {_CARD_BG};
    color: #666666;
    text-align: left;
    padding: 0px 0px 0px 22px;
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 3px;
}}
QPushButton:hover {{
    background: #1d1d1d;
    color: #aaaaaa;
    border-left: 3px solid #2e2e2e;
}}
"""

_CARD_ACTIVE = f"""
QPushButton {{
    background: #0b2520;
    border: none;
    border-left: 3px solid {_ACCENT};
    color: {_ACCENT};
    text-align: left;
    padding: 0px 0px 0px 22px;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 3px;
}}
"""

_CYCLE_OFF = f"""
QPushButton {{
    background: {_CARD_BG};
    border: 1px solid #222222;
    border-radius: 5px;
    color: #444444;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 4px;
}}
QPushButton:hover {{
    border-color: #383838;
    color: #777777;
}}
"""

_CYCLE_ON = f"""
QPushButton {{
    background: #0b2520;
    border: 1px solid {_ACCENT};
    border-radius: 5px;
    color: {_ACCENT};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 4px;
}}
"""

_STATUS_COLOR = {
    "disconnected": "#383838",
    "connecting":   "#c88020",
    "connected":    _ACCENT,
    "error":        "#c04040",
}
_STATUS_TEXT = {
    "disconnected": "DISCONNECTED",
    "connecting":   "CONNECTING",
    "connected":    "CONNECTED",
    "error":        "ERROR",
}


def _demo_display_name(path: Path) -> str:
    stem = path.name.split(".")[0]
    return stem.split("_", 1)[-1].upper()


def _make_panel_btn(text: str, color: str) -> str:
    bg = color + "18"   # ~10% opacity tint
    return f"""
QPushButton {{
    background: {_CARD_BG};
    border: 1px solid #222222;
    border-radius: 5px;
    color: #444444;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 4px;
}}
QPushButton:hover {{
    border-color: {color};
    color: {color};
    background: {bg};
}}
"""


def _make_panel_btn_active(color: str) -> str:
    bg = color + "18"
    return f"""
QPushButton {{
    background: {bg};
    border: 1px solid {color};
    border-radius: 5px;
    color: {color};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 4px;
}}
"""


class _DemoCard(QPushButton):
    def __init__(self, path: Path, parent=None):
        super().__init__(_demo_display_name(path), parent)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_CARD_INACTIVE)

    def set_active(self, active: bool) -> None:
        self.setStyleSheet(_CARD_ACTIVE if active else _CARD_INACTIVE)


def _centered(widget: QWidget, btn_width: int = 200) -> QWidget:
    widget.setFixedWidth(btn_width)
    row = QWidget()
    row_layout = QHBoxLayout(row)
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.addStretch()
    row_layout.addWidget(widget)
    row_layout.addStretch()
    return row


class TouchWindow(QMainWindow):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.tcp = TcpClient(self, debug=True)
        self.demo_files: list[Path] = []
        self.demo_cards: list[_DemoCard] = []
        self.active_index: int = -1
        self.cycle_index: int = 0
        self._base_pins: list[Pin] | None = None
        self._theme_index: int = 0
        self._auto_reconnect: bool = True

        self.cycle_timer = QTimer(self)
        self.cycle_timer.setInterval(DEFAULT_CYCLE_SECONDS * 1000)
        self.cycle_timer.timeout.connect(self._advance_cycle)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(5000)
        self._reconnect_timer.timeout.connect(self._try_reconnect)

        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(20)
        self._anim_timer.timeout.connect(self._anim_step)
        self._anim_index: int = 0
        self._anim_mode: str = 'color'        # 'color' | 'demo'
        self._anim_new_colors: list[tuple] = []  # (r, g, b) per pin, used in demo mode

        self._trans_timer = QTimer(self)
        self._trans_timer.setInterval(TRANSITION_STEP_MS)
        self._trans_timer.timeout.connect(self._trans_step)
        self._trans_new_heights: list[float] = [0.0] * 64
        self._trans_current_heights: list[float] = [0.0] * 64
        self._trans_speed: float = 0.0   # mm per step, same for every pin

        self.setWindowTitle("PinScope")
        self._apply_theme()
        self._setup_ui()
        self._load_demos()

        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._toggle_fullscreen)

        self.tcp.status_changed.connect(self._on_status_changed)
        self.tcp.connect_to(KIOSK_HOST, KIOSK_PORT)
        self._reconnect_timer.start()

        self.showFullScreen()

    # ── Theme ─────────────────────────────────────────────────────────

    def _apply_theme(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{ background: {_BG}; color: {_TEXT}; border: none; }}
            QLabel {{ background: transparent; }}
        """)

    # ── UI construction ───────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        main_row = QWidget()
        row_layout = QHBoxLayout(main_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        self.view_3d = View3D(self.app_state)
        self.view_3d.reset_btn.hide()
        row_layout.addWidget(self.view_3d, stretch=1)

        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet(f"background: {_DIVIDER};")
        row_layout.addWidget(sep)

        row_layout.addWidget(self._build_right_panel())

        outer.addWidget(main_row, stretch=1)
        outer.addWidget(self._build_status_bar())
        self.setCentralWidget(root)

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(256)
        panel.setStyleSheet(f"background: {_PANEL_BG};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 36, 0, 28)
        layout.setSpacing(0)

        # Demos heading + cards
        heading = QLabel("DEMOS")
        heading.setStyleSheet(f"""
            color: {_SUBTEXT};
            font-size: 9px;
            font-weight: 700;
            letter-spacing: 5px;
            padding-left: 26px;
            padding-bottom: 20px;
        """)
        layout.addWidget(heading)

        self.cards_container = QWidget()
        cards_layout = QVBoxLayout(self.cards_container)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(1)
        self.cards_layout = cards_layout
        layout.addWidget(self.cards_container)

        layout.addStretch()

        # ── Divider ───────────────────────────────────────────────────
        layout.addWidget(self._divider())
        layout.addSpacing(20)

        # Change Color button
        self.color_btn = QPushButton("CHANGE  COLOR")
        self.color_btn.setFixedHeight(42)
        self.color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.color_btn.clicked.connect(self._on_change_color)
        layout.addWidget(_centered(self.color_btn))
        self._refresh_color_btn()

        layout.addSpacing(10)

        # Auto Cycle toggle
        self.cycle_btn = QPushButton("AUTO  CYCLE")
        self.cycle_btn.setCheckable(True)
        self.cycle_btn.setFixedHeight(42)
        self.cycle_btn.setStyleSheet(_CYCLE_OFF)
        self.cycle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cycle_btn.toggled.connect(self._on_cycle_toggled)
        layout.addWidget(_centered(self.cycle_btn))

        layout.addSpacing(20)

        # ── Divider ───────────────────────────────────────────────────
        layout.addWidget(self._divider())
        layout.addSpacing(20)

        # Connect / Disconnect button
        self.connect_btn = QPushButton("CONNECT")
        self.connect_btn.setFixedHeight(42)
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setStyleSheet(_make_panel_btn("CONNECT", _ACCENT))
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(_centered(self.connect_btn))

        return panel

    def _build_status_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(42)
        bar.setStyleSheet(f"background: #090909; border-top: 1px solid {_DIVIDER};")

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(10)

        self.status_dot = QLabel()
        self.status_dot.setFixedSize(7, 7)
        self.status_dot.setStyleSheet("background: #383838; border-radius: 3px;")
        layout.addWidget(self.status_dot)

        self.status_label = QLabel("DISCONNECTED")
        self.status_label.setStyleSheet(
            "color: #383838; font-size: 9px; letter-spacing: 3px; font-weight: 500;"
        )
        layout.addWidget(self.status_label)

        self.sep_dot = QLabel("·")
        self.sep_dot.setStyleSheet(f"color: {_SUBTEXT}; font-size: 12px;")
        self.sep_dot.setVisible(False)
        layout.addWidget(self.sep_dot)

        self.demo_label = QLabel("")
        self.demo_label.setStyleSheet(
            f"color: {_SUBTEXT}; font-size: 9px; letter-spacing: 3px; font-weight: 500;"
        )
        layout.addWidget(self.demo_label)

        layout.addStretch()

        reset_btn = QPushButton("RESET ALL")
        reset_btn.setFixedSize(90, 26)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid #202020;
                border-radius: 4px;
                color: #383838;
                font-size: 9px;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                border-color: #a03030;
                color: #c04040;
            }}
        """)
        reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(reset_btn)

        return bar

    def _divider(self) -> QWidget:
        d = QWidget()
        d.setFixedHeight(1)
        d.setStyleSheet(f"background: {_DIVIDER};")
        return d

    # ── Demo loading ──────────────────────────────────────────────────

    def _load_demos(self) -> None:
        self.demo_files = sorted(CYCLE_DEMO_DIR.glob("*.pinscope.json"))
        for path in self.demo_files:
            card = _DemoCard(path)
            card.clicked.connect(lambda checked=False, p=path: self._select_demo(p))
            self.cards_layout.addWidget(card)
            self.demo_cards.append(card)

    # ── Actions ───────────────────────────────────────────────────────

    def _select_demo(self, path: Path) -> None:
        self._stop_cycle()
        self._load_and_deploy(path)

    def _load_and_deploy(self, path: Path) -> bool:
        self._anim_timer.stop()
        self._trans_timer.stop()
        try:
            new_design = design_io.load(path)
        except Exception:
            return False

        # Capture old heights before replacing the design.
        old_heights = [float(p.height) for p in self.app_state.design.pins]
        new_heights = [float(p.height) for p in new_design.pins]

        # Capture old colors before the design is replaced.
        old_colors = [(p.r, p.g, p.b) for p in self.app_state.design.pins]
        new_colors  = [(p.r, p.g, p.b) for p in new_design.pins]

        # Apply new design so app_state is immediately consistent.
        self.app_state.set_design(new_design)

        # Send hardware commands now with the correct final state.
        if self.tcp.is_connected:
            self._send_current()

        # Revert both heights AND colors to the old values so both animations
        # start from the previous demo's appearance.
        design = self.app_state.design
        for i in range(64):
            r, g, b = old_colors[i]
            design.pins[i] = Pin(max(1, int(old_heights[i])), r, g, b)
        self.app_state.design_changed.emit()

        # Store final state as base_pins for color cycling.
        self._base_pins = [Pin(int(new_heights[i]), *new_colors[i]) for i in range(64)]
        self._theme_index = 0
        self._refresh_color_btn()

        # Start height transition — constant speed, same mm/step for every pin.
        # TRANSITION_MS defines how long the longest-travel pin takes.
        max_dist = max((abs(new_heights[i] - old_heights[i]) for i in range(64)), default=1.0)
        steps = max(1.0, TRANSITION_MS / TRANSITION_STEP_MS)
        self._trans_speed = max_dist / steps
        self._trans_new_heights = new_heights
        self._trans_current_heights = list(old_heights)
        self._trans_timer.start()

        # Start color sweep (pin by pin, same cadence as Change Color).
        self._anim_mode = 'demo'
        self._anim_new_colors = new_colors
        self._anim_index = 0
        self._anim_timer.start()

        idx = next((i for i, f in enumerate(self.demo_files) if f == path), -1)
        self.active_index = idx
        for i, card in enumerate(self.demo_cards):
            card.set_active(i == idx)

        self.demo_label.setText(_demo_display_name(path))
        self.sep_dot.setVisible(True)
        return True

    def _trans_step(self) -> None:
        design = self.app_state.design
        all_done = True

        for i in range(64):
            target  = self._trans_new_heights[i]
            current = self._trans_current_heights[i]
            diff    = target - current

            if abs(diff) <= self._trans_speed:
                self._trans_current_heights[i] = target   # snap to final
            else:
                self._trans_current_heights[i] = current + self._trans_speed * (1.0 if diff > 0 else -1.0)
                all_done = False

            p = design.pins[i]
            design.pins[i] = Pin(max(1, int(self._trans_current_heights[i])), p.r, p.g, p.b)

        self.app_state.design_changed.emit()

        if all_done:
            self._trans_timer.stop()

    def _send_current(self) -> None:
        d = self.app_state.design
        self.tcp.send(";".join(serialize_heights(d)) + "\r\n")
        self.tcp.send(";".join(serialize_colors(d)) + "\r\n")

    # ── Color cycling ─────────────────────────────────────────────────

    def _on_change_color(self) -> None:
        if not self._base_pins:
            return
        self._anim_timer.stop()
        # Snap all pins to their final heights if a transition is still running.
        if self._trans_timer.isActive():
            self._trans_timer.stop()
            design = self.app_state.design
            for i, h in enumerate(self._trans_new_heights):
                p = design.pins[i]
                design.pins[i] = Pin(max(1, int(h)), p.r, p.g, p.b)
            self.app_state.design_changed.emit()

        self._theme_index = (self._theme_index + 1) % len(_THEMES)
        theme = _THEMES[self._theme_index]
        design = self.app_state.design

        # Apply all new colors to design upfront so state is consistent.
        for i, base in enumerate(self._base_pins):
            if theme is None:
                design.pins[i] = Pin(base.height, base.r, base.g, base.b)
            else:
                r, g, b = _gradient_color(base.height, theme["stops"])
                design.pins[i] = Pin(base.height, r, g, b)

        if self.tcp.is_connected:
            self.tcp.send(";".join(serialize_colors(design)) + "\r\n")

        self._anim_mode = 'color'
        self._anim_index = 0
        self._anim_timer.start()
        self._refresh_color_btn()

    def _anim_step(self) -> None:
        i = self._anim_index
        if i >= 64:
            self._anim_timer.stop()
            return

        design = self.app_state.design
        if self._anim_mode == 'color':
            # Design already has final colors; just reveal them one pin at a time.
            # TCP messages were already queued atomically in _on_change_color.
            self.app_state.pin_changed.emit(i)
        else:  # 'demo'
            # Sweep in the new color while keeping the current interpolated height.
            r, g, b = self._anim_new_colors[i]
            p = design.pins[i]
            design.pins[i] = Pin(p.height, r, g, b)
            self.app_state.pin_changed.emit(i)

        self._anim_index += 1

    def _refresh_color_btn(self) -> None:
        theme = _THEMES[self._theme_index]
        if theme is None:
            self.color_btn.setText("CHANGE  COLOR")
            self.color_btn.setStyleSheet(_make_panel_btn("CHANGE  COLOR", _ACCENT))
        else:
            self.color_btn.setText(theme["name"])
            self.color_btn.setStyleSheet(_make_panel_btn_active(theme["hint"]))

    # ── Cycle ─────────────────────────────────────────────────────────

    def _on_cycle_toggled(self, checked: bool) -> None:
        if checked:
            self.cycle_btn.setStyleSheet(_CYCLE_ON)
            self.cycle_index = 0
            self._advance_cycle()
            self.cycle_timer.start()
        else:
            self._stop_cycle()

    def _stop_cycle(self) -> None:
        self.cycle_timer.stop()
        if self.cycle_btn.isChecked():
            self.cycle_btn.blockSignals(True)
            self.cycle_btn.setChecked(False)
            self.cycle_btn.blockSignals(False)
        self.cycle_btn.setStyleSheet(_CYCLE_OFF)

    def _advance_cycle(self) -> None:
        if not self.demo_files:
            return
        path = self.demo_files[self.cycle_index % len(self.demo_files)]
        self.cycle_index = (self.cycle_index + 1) % len(self.demo_files)
        self._load_and_deploy(path)

    # ── Reset ─────────────────────────────────────────────────────────

    def _on_reset(self) -> None:
        self._anim_timer.stop()
        self._trans_timer.stop()
        self._stop_cycle()
        self.app_state.reset_all_pins()
        self._base_pins = None
        self._theme_index = 0
        self._refresh_color_btn()
        if self.tcp.is_connected:
            self._send_current()
        for card in self.demo_cards:
            card.set_active(False)
        self.active_index = -1
        self.demo_label.setText("")
        self.sep_dot.setVisible(False)

    # ── Connection ────────────────────────────────────────────────────

    def _on_connect_clicked(self) -> None:
        if self.tcp.is_connected:
            self._auto_reconnect = False
            self._reconnect_timer.stop()
            self.tcp.disconnect_from()
        else:
            self._auto_reconnect = True
            self.tcp.connect_to(KIOSK_HOST, KIOSK_PORT)
            if not self._reconnect_timer.isActive():
                self._reconnect_timer.start()

    def _try_reconnect(self) -> None:
        if self._auto_reconnect and not self.tcp.is_connected:
            self.tcp.connect_to(KIOSK_HOST, KIOSK_PORT)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    # ── Status ────────────────────────────────────────────────────────

    def _on_status_changed(self, status: str) -> None:
        color = _STATUS_COLOR.get(status, "#383838")
        label = _STATUS_TEXT.get(status, status.upper())

        self.status_dot.setStyleSheet(f"background: {color}; border-radius: 3px;")
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 9px; letter-spacing: 3px; font-weight: 500;"
        )
        self.status_label.setText(label)

        if status == "connected":
            self._reconnect_timer.stop()
            self.connect_btn.setText("DISCONNECT")
            self.connect_btn.setStyleSheet(_make_panel_btn_active(_ACCENT))
        else:
            self.connect_btn.setText("CONNECT")
            self.connect_btn.setStyleSheet(_make_panel_btn("CONNECT", _ACCENT))
            if status in ("disconnected", "error") and self._auto_reconnect:
                if not self._reconnect_timer.isActive():
                    self._reconnect_timer.start()
