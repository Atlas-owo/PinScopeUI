from pinscope.model.pin import Pin
from pinscope.model.design import Design

def test_pin_defaults():
    pin = Pin()
    assert pin.height == 0
    assert pin.r == 255
    assert pin.g == 255
    assert pin.b == 255

def test_design_defaults():
    design = Design()
    assert design.name == "Untitled"
    assert len(design.pins) == 64
    assert design.motor_start_speed == 500
    assert design.motor_end_speed == 200
    assert design.global_brightness == 200
    assert design.schema_version == 1
    for pin in design.pins:
        assert pin.height == 0
