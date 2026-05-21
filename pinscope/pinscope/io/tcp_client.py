from __future__ import annotations
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket


class TcpClient(QObject):
    # Emitted whenever connection state changes
    status_changed = Signal(str)   # "disconnected" | "connecting" | "connected" | "error"
    error_occurred = Signal(str)   # human-readable error message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._socket = QTcpSocket(self)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.errorOccurred.connect(self._on_error)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._socket.state() == QAbstractSocket.SocketState.ConnectedState

    def connect_to(self, host: str, port: int) -> None:
        if self.is_connected:
            self._socket.disconnectFromHost()
        self.status_changed.emit("connecting")
        self._socket.connectToHost(host, port)

    def disconnect_from(self) -> None:
        self._socket.disconnectFromHost()

    def send(self, message: str) -> bool:
        if not self.is_connected:
            return False
        data = message.encode("utf-8")
        self._socket.write(data)
        return True

    def send_all(self, messages: list[str]) -> bool:
        if not self.is_connected:
            return False
        payload = "".join(messages).encode("utf-8")
        self._socket.write(payload)
        return True

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _on_connected(self) -> None:
        self.status_changed.emit("connected")

    def _on_disconnected(self) -> None:
        self.status_changed.emit("disconnected")

    def _on_error(self, error: QAbstractSocket.SocketError) -> None:
        msg = self._socket.errorString()
        self.error_occurred.emit(msg)
        self.status_changed.emit("error")
