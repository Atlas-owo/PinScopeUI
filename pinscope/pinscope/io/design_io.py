from __future__ import annotations
import json
from pathlib import Path
from ..model.design import Design
from ..model.pin import Pin

class DesignIOError(Exception):
    pass

class UnsupportedSchemaError(DesignIOError):
    pass

class InvalidGridSizeError(DesignIOError):
    pass

def save(path: str | Path, design: Design) -> None:
    data = {
        "schema_version": design.schema_version,
        "name": design.name,
        "grid_size": [8, 8],
        "pins": [
            {"height": p.height, "r": p.r, "g": p.g, "b": p.b}
            for p in design.pins
        ],
        "motor_speed": design.motor_speed,
        "global_brightness": design.global_brightness
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
        
    design = Design(
        name=data.get("name", "Untitled"),
        motor_speed=data.get("motor_speed", 128),
        global_brightness=data.get("global_brightness", 200),
        schema_version=schema_version
    )
    
    pin_data = data.get("pins", [])
    if len(pin_data) != 64:
        raise DesignIOError(f"Expected 64 pins, got {len(pin_data)}")
        
    pins = []
    for pd in pin_data:
        pins.append(Pin(
            height=pd.get("height", 0),
            r=pd.get("r", 0),
            g=pd.get("g", 0),
            b=pd.get("b", 0)
        ))
    design.pins = pins
    
    return design
