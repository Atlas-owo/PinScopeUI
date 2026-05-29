from __future__ import annotations
from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket

_SEND_INTERVAL_MS = 20


class TcpClient(QObject):
    # Emitted whenever connection state changes
    status_changed = Signal(str)   # "disconnected" | "connecting" | "connected" | "error"
    error_occurred = Signal(str)   # human-readable error message

    def __init__(self, parent: QObject | None = None, debug: bool = False) -> None:
        super().__init__(parent)
        self._debug = debug
        self._queue: deque[str] = deque()

        self._socket = QTcpSocket(self)
        self._socket.connected.connect(self._on_connected)
        self._socket.disconnected.connect(self._on_disconnected)
        self._socket.errorOccurred.connect(self._on_error)
        self._socket.readyRead.connect(self._on_ready_read)

        self._timer = QTimer(self)
        self._timer.setInterval(_SEND_INTERVAL_MS)
        self._timer.timeout.connect(self._flush_one)

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
        self._queue.clear()
        self._timer.stop()
        self._socket.disconnectFromHost()

    def send(self, message: str) -> bool:
        if not self.is_connected:
            return False
        self._queue.append(message)
        if not self._timer.isActive():
            self._timer.start()
        return True

    def send_all(self, messages: list[str]) -> bool:
        if not self.is_connected:
            return False
        self._queue.extend(messages)
        if not self._timer.isActive():
            self._timer.start()
        return True

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------

    def _flush_one(self) -> None:
        if not self._queue or not self.is_connected:
            self._timer.stop()
            return
        message = self._queue.popleft()
        if self._debug:
            print(f"[TCP →] {message}", end="", flush=True)
        self._socket.write(message.encode("utf-8"))
        self._socket.flush()

    def _on_connected(self) -> None:
        if self._debug:
            print(f"[TCP] Connected to {self._socket.peerName()}:{self._socket.peerPort()}", flush=True)
        self.status_changed.emit("connected")

    def _on_disconnected(self) -> None:
        self._queue.clear()
        self._timer.stop()
        if self._debug:
            print("[TCP] Disconnected", flush=True)
        self.status_changed.emit("disconnected")

    def _on_error(self, error: QAbstractSocket.SocketError) -> None:
        msg = self._socket.errorString()
        if self._debug:
            print(f"[TCP] Error: {msg}", flush=True)
        self.error_occurred.emit(msg)
        self.status_changed.emit("error")

    def _on_ready_read(self) -> None:
        while self._socket.canReadLine():
            line = self._socket.readLine().data().decode("utf-8", errors="replace").rstrip("\r\n")
            if self._debug:
                print(f"[TCP ←] {line}", flush=True)
