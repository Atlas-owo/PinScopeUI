from __future__ import annotations
from dataclasses import dataclass, field
from .pin import Pin

@dataclass
class Design:
    name: str = "Untitled"
    pins: list[Pin] = field(default_factory=lambda: [Pin() for _ in range(64)])
    motor_speed: int = 128
    global_brightness: int = 200
    schema_version: int = 1
