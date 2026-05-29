from __future__ import annotations
import json
from ..model.design import Design

# ---------------------------------------------------------------------------
# Pin → board mapping
#
# Physical layout: 8 modules in a 4-row × 2-col grid.
# Each module is 4 cols × 2 rows of pins → total 8×8 pin grid.
#
# Module numbering (row-major, 1-based):
#   mod1 mod2   (rows 0-1,  cols 0-3 / 4-7)
#   mod3 mod4   (rows 2-3,  cols 0-3 / 4-7)
#   mod5 mod6   (rows 4-5,  cols 0-3 / 4-7)
#   mod7 mod8   (rows 6-7,  cols 0-3 / 4-7)
#
# Within each module, motor IDs:
#   1  3  5  7
#   2  4  6  8
#
# Derivation for pin at (row, col):
#   board_i  = (row // 2) * 2 + (col // 4) + 1    →  1..8  (0 is broadcast)
#   motor_id = (col % 4) * 2 + (row % 2) + 1      →  1..8
# ---------------------------------------------------------------------------

def _pin_to_board(row: int, col: int) -> tuple[int, int]:
    board_i = (row // 2) * 2 + (col // 4) + 1      # 1-based: 1..8
    motor_id = (col % 4) * 2 + (row % 2) + 1        # 1-based: 1..8
    return board_i, motor_id


def _make_msg(i: int, s: int, h: list[int]) -> str:
    return json.dumps({"i": i, "s": s, "h": h}, separators=(",", ":"))


def serialize_heights(design: Design) -> list[str]:
    """Return one s:1 message per board with the 8 pin heights in motor-ID order."""
    # board_heights[board_i][motor_id] = height  (board 0-based, motor 1-based)
    board_heights: dict[int, dict[int, int]] = {i: {} for i in range(1, 9)}

    for idx, pin in enumerate(design.pins):
        row, col = divmod(idx, 8)
        board_i, motor_id = _pin_to_board(row, col)
        board_heights[board_i][motor_id] = pin.height

    messages = []
    for board_i in range(1, 9):
        h = [board_heights[board_i].get(m, 0) for m in range(1, 9)]
        messages.append(_make_msg(board_i, 1, h))
    return messages


def serialize_colors(design: Design) -> list[str]:
    """Return one s:9 message per pin (64 total) to set each motor's LED color."""
    messages = []
    for idx, pin in enumerate(design.pins):
        row, col = divmod(idx, 8)
        board_i, motor_id = _pin_to_board(row, col)
        # s:9 format: h[0]=motor_id, h[1]=R, h[2]=G, h[3]=B, h[4-6]=0, h[7]=reset_flag
        h = [motor_id, pin.r, pin.g, pin.b, 0, 0, 0, 0]
        messages.append(_make_msg(board_i, 9, h))
    return messages


def serialize_motor_speed(start: int, end: int) -> str:
    """s:5 broadcast — ramp from start to end speed."""
    # Protocol encodes each value as two digits: e.g. 500 → [5, 00]
    # We send the raw integer values directly as the hardware expects.
    h = [start // 100, start % 100, end // 100, end % 100, 0, 0, 0, 0]
    return _make_msg(0, 5, h)


def serialize_gesture(design: Design) -> list[str]:
    """s:8 broadcast — push (UP) and pull (DOWN) gesture config."""
    p = design.push_config
    pu = design.pull_config
    h = [
        p.direction, p.step_height, p.r, p.g, p.b,
        pu.direction, pu.step_height, pu.r, pu.g, pu.b,
    ]
    return [_make_msg(0, 8, h)]


def serialize_full_deploy(design: Design) -> list[str]:
    """Heights and colors only. Speed and gesture are sent via dedicated buttons."""
    messages = []
    messages += serialize_heights(design)
    messages += serialize_colors(design)
    return messages
