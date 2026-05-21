from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton,
)
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QColor
from ..io.tcp_client import TcpClient
from ..app_state import AppState
from ..protocol.commands import serialize_full_deploy

DEFAULT_HOST = "192.168.0.10"
DEFAULT_PORT = 5000

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

        # Deploy button
        self.deploy_btn = QPushButton("Deploy")
        self.deploy_btn.setFixedWidth(80)
        self.deploy_btn.setEnabled(False)
        self.deploy_btn.clicked.connect(self._on_deploy)
        layout.addWidget(self.deploy_btn)

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
        messages = serialize_full_deploy(self.app_state.design)
        self.tcp.send_all(messages)

    def _on_status_changed(self, status: str):
        self._apply_status(status)

    def _on_error(self, message: str):
        self.status_label.setToolTip(message)

    def _apply_status(self, status: str):
        self.status_dot.setStyleSheet(_STATUS_STYLE.get(status, _STATUS_STYLE["disconnected"]))
        self.status_label.setText(_STATUS_LABEL.get(status, status))
        connected = (status == "connected")
        self.deploy_btn.setEnabled(connected)
        self.connect_btn.setText("Disconnect" if connected else "Connect")
        # Disable host/port while connected or connecting
        editable = status in ("disconnected", "error")
        self.host_edit.setEnabled(editable)
        self.port_spin.setEnabled(editable)
