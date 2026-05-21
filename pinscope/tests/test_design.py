from pinscope.model.pin import Pin
from pinscope.model.design import Design

def test_pin_defaults():
    pin = Pin()
    assert pin.height == 0
    assert pin.r == 0
    assert pin.g == 0
    assert pin.b == 0

def test_design_defaults():
    design = Design()
    assert design.name == "Untitled"
    assert len(design.pins) == 64
    assert design.motor_speed == 128
    assert design.global_brightness == 200
    assert design.schema_version == 1
    
    # Check that pins are initialized correctly
    for pin in design.pins:
        assert pin.height == 0
