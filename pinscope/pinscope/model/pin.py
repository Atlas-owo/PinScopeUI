from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Pin:
    height: int = 0  # 0–255
    r: int = 0       # 0–255
    g: int = 0       # 0–255
    b: int = 0       # 0–255
