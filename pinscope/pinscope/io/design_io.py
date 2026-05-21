from __future__ import annotations
import json
from pathlib import Path
from ..model.design import Design
from ..model.pin import Pin
from ..model.gesture import GestureConfig

class DesignIOError(Exception):
    pass

class UnsupportedSchemaError(DesignIOError):
    pass

class InvalidGridSizeError(DesignIOError):
    pass

def _gesture_to_dict(g: GestureConfig) -> dict:
    return {"direction": g.direction, "step_height": g.step_height, "r": g.r, "g": g.g, "b": g.b}

def _dict_to_gesture(d: dict, default: GestureConfig) -> GestureConfig:
    return GestureConfig(
        direction=d.get("direction", default.direction),
        step_height=d.get("step_height", default.step_height),
        r=d.get("r", default.r),
        g=d.get("g", default.g),
        b=d.get("b", default.b),
    )

def save(path: str | Path, design: Design) -> None:
    data = {
        "schema_version": design.schema_version,
        "name": design.name,
        "grid_size": [8, 8],
        "pins": [
            {"height": p.height, "r": p.r, "g": p.g, "b": p.b}
            for p in design.pins
        ],
        "motor_start_speed": design.motor_start_speed,
        "motor_end_speed": design.motor_end_speed,
        "global_brightness": design.global_brightness,
        "push_config": _gesture_to_dict(design.push_config),
        "pull_config": _gesture_to_dict(design.pull_config),
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def load(path: str | Path) -> Design:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    schema_version = data.get("schema_version", 1)
    if schema_version != 1:
        raise UnsupportedSchemaError(f"Unsupported schema version: {schema_version}")

    grid_size = data.get("grid_size", [8, 8])
    if grid_size != [8, 8]:
        raise InvalidGridSizeError(f"Unsupported grid size: {grid_size}. Only [8, 8] is supported.")

    default_push = GestureConfig(direction=1, step_height=50, r=255, g=255, b=255)
    default_pull = GestureConfig(direction=0, step_height=50, r=0, g=128, b=255)

    design = Design(
        name=data.get("name", "Untitled"),
        motor_start_speed=data.get("motor_start_speed", data.get("motor_speed", 500)),
        motor_end_speed=data.get("motor_end_speed", 200),
        global_brightness=data.get("global_brightness", 200),
        push_config=_dict_to_gesture(data.get("push_config", {}), default_push),
        pull_config=_dict_to_gesture(data.get("pull_config", {}), default_pull),
        schema_version=schema_version,
    )

    pin_data = data.get("pins", [])
    if len(pin_data) != 64:
        raise DesignIOError(f"Expected 64 pins, got {len(pin_data)}")

    design.pins = [
        Pin(height=pd.get("height", 0), r=pd.get("r", 0), g=pd.get("g", 0), b=pd.get("b", 0))
        for pd in pin_data
    ]

    return design
