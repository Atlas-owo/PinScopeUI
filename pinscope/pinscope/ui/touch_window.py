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
from ..protocol.commands import serialize_heights, serialize_colors

KIOSK_HOST = "192.168.0.10"
KIOSK_PORT = 5000
CYCLE_DEMO_DIR = Path(__file__).resolve().parents[3] / "presets" / "cycle_demo"
DEFAULT_CYCLE_SECONDS = 30

_BG        = "#0d0d0d"
_PANEL_BG  = "#101010"
_DIVIDER   = "#1a1a1a"
_ACCENT    = "#00c6a7"
_CARD_BG   = "#161616"
_TEXT      = "#dddddd"
_SUBTEXT   = "#444444"

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
    stem = path.name.split(".")[0]          # "01_Checkerboard"
    return stem.split("_", 1)[-1].upper()   # "CHECKERBOARD"


class _DemoCard(QPushButton):
    def __init__(self, path: Path, parent=None):
        super().__init__(_demo_display_name(path), parent)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(_CARD_INACTIVE)

    def set_active(self, active: bool) -> None:
        self.setStyleSheet(_CARD_ACTIVE if active else _CARD_INACTIVE)


class TouchWindow(QMainWindow):
    def __init__(self, app_state: AppState, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.tcp = TcpClient(self, debug=True)
        self.demo_files: list[Path] = []
        self.demo_cards: list[_DemoCard] = []
        self.active_index: int = -1
        self.cycle_index: int = 0

        self.cycle_timer = QTimer(self)
        self.cycle_timer.setInterval(DEFAULT_CYCLE_SECONDS * 1000)
        self.cycle_timer.timeout.connect(self._advance_cycle)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(5000)
        self._reconnect_timer.timeout.connect(self._try_reconnect)

        self.setWindowTitle("PinScope")
        self._apply_theme()
        self._setup_ui()
        self._load_demos()

        # Esc exits fullscreen (useful during development)
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

        # Main row: 3D view + right panel
        main_row = QWidget()
        row_layout = QHBoxLayout(main_row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(0)

        self.view_3d = View3D(self.app_state)
        self.view_3d.reset_btn.hide()   # hide the floating reset-camera button
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

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_DIVIDER};")
        layout.addWidget(sep)
        layout.addSpacing(24)

        self.cycle_btn = QPushButton("AUTO  CYCLE")
        self.cycle_btn.setCheckable(True)
        self.cycle_btn.setFixedSize(200, 42)
        self.cycle_btn.setStyleSheet(_CYCLE_OFF)
        self.cycle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cycle_btn.toggled.connect(self._on_cycle_toggled)

        cycle_row = QWidget()
        cycle_row_layout = QHBoxLayout(cycle_row)
        cycle_row_layout.setContentsMargins(0, 0, 0, 0)
        cycle_row_layout.addStretch()
        cycle_row_layout.addWidget(self.cycle_btn)
        cycle_row_layout.addStretch()
        layout.addWidget(cycle_row)

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

        self.reset_btn = QPushButton("RESET ALL")
        self.reset_btn.setFixedSize(90, 26)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.setStyleSheet(f"""
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
        self.reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(self.reset_btn)

        return bar

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
        try:
            design = design_io.load(path)
        except Exception:
            return False

        self.app_state.set_design(design)

        idx = next((i for i, f in enumerate(self.demo_files) if f == path), -1)
        self.active_index = idx
        for i, card in enumerate(self.demo_cards):
            card.set_active(i == idx)

        name = _demo_display_name(path)
        self.demo_label.setText(name)
        self.sep_dot.setVisible(True)

        if self.tcp.is_connected:
            self._send_current()
        return True

    def _send_current(self) -> None:
        d = self.app_state.design
        self.tcp.send(";".join(serialize_heights(d)) + "\r\n")
        self.tcp.send(";".join(serialize_colors(d)) + "\r\n")

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

    def _on_reset(self) -> None:
        self._stop_cycle()
        self.app_state.reset_all_pins()
        if self.tcp.is_connected:
            self._send_current()
        for card in self.demo_cards:
            card.set_active(False)
        self.active_index = -1
        self.demo_label.setText("")
        self.sep_dot.setVisible(False)

    def _try_reconnect(self) -> None:
        if not self.tcp.is_connected:
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
        elif status in ("disconnected", "error"):
            if not self._reconnect_timer.isActive():
                self._reconnect_timer.start()
