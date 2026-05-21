from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Pin:
    height: int = 0    # 0–200 mm
    r: int = 255       # 0–255
    g: int = 255       # 0–255
    b: int = 255       # 0–255
