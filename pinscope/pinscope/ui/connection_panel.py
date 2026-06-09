from __future__ import annotations
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton, QMessageBox,
)
from PySide6.QtCore import QSettings, QTimer
from ..io.tcp_client import TcpClient
from ..app_state import AppState
from ..protocol.commands import serialize_heights, serialize_colors, serialize_motor_speed, serialize_gesture
from ..io import design_io

DEFAULT_HOST = "192.168.0.10"
DEFAULT_PORT = 5000
DEFAULT_CYCLE_SECONDS = 60
CYCLE_DEMO_DIR = Path(__file__).resolve().parents[3] / "presets" / "cycle_demo"

# Status dot colors
_STATUS_STYLE = {
    "disconnected": "background:#888;    border-radius:6px;",
    "connecting":   "background:#f0c040; border-radius:6px;",
    "connected":    "background:#40c040; border-radius:6px;",
    "error":        "background:#e04040; border-radius:6px;",
}
_STATUS_LABEL = {
    "disconnected": "Disconnected",
    "connecting":   "Connecting…",
    "connected":    "Connected",
    "error":        "Error",
}


class ConnectionPanel(QWidget):
    def __init__(self, app_state: AppState, tcp_client: TcpClient, parent=None):
        super().__init__(parent)
        self.app_state = app_state
        self.tcp = tcp_client
        self.settings = QSettings("MIT", "PinScope")
        self.cycle_files: list[Path] = []
        self.cycle_index = 0
        self.cycle_timer = QTimer(self)
        self.cycle_timer.timeout.connect(self._advance_cycle)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)

        # Status indicator dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(12, 12)
        layout.addWidget(self.status_dot)

        # Status text
        self.status_label = QLabel("Disconnected")
        self.status_label.setMinimumWidth(90)
        layout.addWidget(self.status_label)

        layout.addSpacing(8)

        # Host
        layout.addWidget(QLabel("Host:"))
        self.host_edit = QLineEdit()
        self.host_edit.setFixedWidth(130)
        self.host_edit.setText(
            self.settings.value("tcp/host", DEFAULT_HOST)
        )
        layout.addWidget(self.host_edit)

        # Port
        layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(
            int(self.settings.value("tcp/port", DEFAULT_PORT))
        )
        self.port_spin.setFixedWidth(70)
        layout.addWidget(self.port_spin)

        # Connect / Disconnect button
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(90)
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_btn)

        layout.addSpacing(16)

        # Deploy button (heights + colors only)
        self.deploy_btn = QPushButton("Deploy")
        self.deploy_btn.setFixedWidth(80)
        self.deploy_btn.setEnabled(False)
        self.deploy_btn.clicked.connect(self._on_deploy)
        layout.addWidget(self.deploy_btn)

        # Send Speed button
        self.speed_btn = QPushButton("Send Speed")
        self.speed_btn.setFixedWidth(90)
        self.speed_btn.setEnabled(False)
        self.speed_btn.clicked.connect(self._on_send_speed)
        layout.addWidget(self.speed_btn)

        # Send Gesture button
        self.gesture_btn = QPushButton("Send Gesture")
        self.gesture_btn.setFixedWidth(100)
        self.gesture_btn.setEnabled(False)
        self.gesture_btn.clicked.connect(self._on_send_gesture)
        layout.addWidget(self.gesture_btn)

        layout.addSpacing(16)

        layout.addWidget(QLabel("Cycle:"))
        self.cycle_interval_spin = QSpinBox()
        self.cycle_interval_spin.setRange(5, 3600)
        self.cycle_interval_spin.setSuffix(" s")
        self.cycle_interval_spin.setValue(
            int(self.settings.value("cycle/interval_seconds", DEFAULT_CYCLE_SECONDS))
        )
        self.cycle_interval_spin.setFixedWidth(80)
        self.cycle_interval_spin.valueChanged.connect(self._on_cycle_interval_changed)
        layout.addWidget(self.cycle_interval_spin)

        self.cycle_btn = QPushButton("Start")
        self.cycle_btn.setCheckable(True)
        self.cycle_btn.setFixedWidth(70)
        self.cycle_btn.toggled.connect(self._on_cycle_toggled)
        layout.addWidget(self.cycle_btn)

        layout.addSpacing(16)

        # Reset All button
        self.reset_btn = QPushButton("Reset All")
        self.reset_btn.setFixedWidth(90)
        self.reset_btn.setStyleSheet("QPushButton { color: #c00; font-weight: bold; }")
        self.reset_btn.clicked.connect(self._on_reset_all)
        layout.addWidget(self.reset_btn)

        layout.addStretch()

        # Wire TCP signals
        self.tcp.status_changed.connect(self._on_status_changed)
        self.tcp.error_occurred.connect(self._on_error)

        self._apply_status("disconnected")

    # ------------------------------------------------------------------

    def _on_connect_clicked(self):
        if self.tcp.is_connected:
            self.tcp.disconnect_from()
        else:
            host = self.host_edit.text().strip()
            port = self.port_spin.value()
            self.settings.setValue("tcp/host", host)
            self.settings.setValue("tcp/port", port)
            self.tcp.connect_to(host, port)

    def _on_deploy(self):
        self._send_current_design()

    def _send_current_design(self):
        design = self.app_state.design
        self.tcp.send(";".join(serialize_heights(design)) + "\r\n")
        self.tcp.send(";".join(serialize_colors(design)) + "\r\n")

    def _on_send_speed(self):
        d = self.app_state.design
        self.tcp.send(serialize_motor_speed(d.motor_start_speed, d.motor_end_speed) + "\r\n")

    def _on_send_gesture(self):
        self.tcp.send(";".join(serialize_gesture(self.app_state.design)) + "\r\n")

    def _on_reset_all(self):
        self.stop_cycle()
        self.app_state.reset_all_pins()
        if self.tcp.is_connected:
            self._send_current_design()

    def _on_cycle_interval_changed(self, seconds: int):
        self.settings.setValue("cycle/interval_seconds", seconds)
        if self.cycle_timer.isActive():
            self.cycle_timer.setInterval(seconds * 1000)

    def _on_cycle_toggled(self, checked: bool):
        if checked:
            self.start_cycle()
        else:
            self.stop_cycle()

    def start_cycle(self):
        self.cycle_files = sorted(CYCLE_DEMO_DIR.glob("*.pinscope.json"))
        if not self.cycle_files:
            self.cycle_btn.blockSignals(True)
            self.cycle_btn.setChecked(False)
            self.cycle_btn.blockSignals(False)
            QMessageBox.warning(
                self,
                "No Cycle Patterns",
                f"No .pinscope.json files found in:\n{CYCLE_DEMO_DIR}",
            )
            return

        self.cycle_index = 0
        self.cycle_btn.setText("Stop")
        self.cycle_interval_spin.setEnabled(False)
        if self._advance_cycle():
            self.cycle_timer.start(self.cycle_interval_spin.value() * 1000)

    def stop_cycle(self):
        if self.cycle_timer.isActive():
            self.cycle_timer.stop()
        if self.cycle_btn.isChecked():
            self.cycle_btn.blockSignals(True)
            self.cycle_btn.setChecked(False)
            self.cycle_btn.blockSignals(False)
        self.cycle_btn.setText("Start")
        self.cycle_interval_spin.setEnabled(True)

    def _advance_cycle(self) -> bool:
        if not self.cycle_files:
            self.stop_cycle()
            return False

        file_path = self.cycle_files[self.cycle_index]
        self.cycle_index = (self.cycle_index + 1) % len(self.cycle_files)
        try:
            self.app_state.set_design(design_io.load(file_path))
        except Exception as e:
            self.stop_cycle()
            QMessageBox.critical(self, "Error Loading Cycle Pattern", f"{file_path.name}\n\n{e}")
            return False

        if self.tcp.is_connected:
            self._send_current_design()
        return True

    def _on_status_changed(self, status: str):
        self._apply_status(status)

    def _on_error(self, message: str):
        self.status_label.setToolTip(message)

    def _apply_status(self, status: str):
        self.status_dot.setStyleSheet(_STATUS_STYLE.get(status, _STATUS_STYLE["disconnected"]))
        self.status_label.setText(_STATUS_LABEL.get(status, status))
        connected = (status == "connected")
        self.deploy_btn.setEnabled(connected)
        self.speed_btn.setEnabled(connected)
        self.gesture_btn.setEnabled(connected)
        self.connect_btn.setText("Disconnect" if connected else "Connect")
        # Disable host/port while connected or connecting
        editable = status in ("disconnected", "error")
        self.host_edit.setEnabled(editable)
        self.port_spin.setEnabled(editable)
