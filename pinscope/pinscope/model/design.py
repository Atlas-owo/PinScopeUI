from __future__ import annotations
from dataclasses import dataclass, field
from .pin import Pin
from .gesture import GestureConfig

@dataclass
class Design:
    name: str = "Untitled"
    pins: list[Pin] = field(default_factory=lambda: [Pin() for _ in range(64)])
    motor_start_speed: int = 500
    motor_end_speed: int = 200
    global_brightness: int = 200
    push_config: GestureConfig = field(default_factory=lambda: GestureConfig(direction=1, step_height=50, r=255, g=255, b=255))
    pull_config: GestureConfig = field(default_factory=lambda: GestureConfig(direction=0, step_height=50, r=0, g=128, b=255))
    schema_version: int = 1
