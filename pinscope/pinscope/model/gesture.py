from __future__ import annotations
from dataclasses import dataclass

@dataclass
class GestureConfig:
    direction: int = 1      # 1=extend, 0=retract
    step_height: int = 50   # mm, 0–200
    r: int = 255
    g: int = 255
    b: int = 255
