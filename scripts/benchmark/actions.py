"""Unified computer-use action schema + pyautogui codegen.

Both model adapters (Anthropic computer_20250124, OpenAI computer-use-preview)
normalize their tool calls into the `Action` types below. `to_pyautogui()` then
renders an action into a Python snippet executed on the VM via
`env.run_python(...)` under DISPLAY=:0.

Coordinate spaces: models reason in the screenshot's pixel space (model_w x
model_h). The VM screen may differ (vm_w x vm_h). We scale click/move/scroll
coordinates from model space to VM space so clicks land correctly. Adapters
should declare the model display size == the screenshot they were given.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# --- Action types -----------------------------------------------------------


@dataclass
class Click:
    x: int
    y: int
    button: str = "left"  # left | right | middle
    clicks: int = 1  # 2 = double-click


@dataclass
class Move:
    x: int
    y: int


@dataclass
class Scroll:
    x: int
    y: int
    dx: int = 0
    dy: int = 0  # positive = down


@dataclass
class Drag:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class TypeText:
    text: str


@dataclass
class KeyPress:
    keys: list[str] = field(default_factory=list)  # e.g. ["ctrl", "c"] (chord) or ["enter"]


@dataclass
class Wait:
    seconds: float = 1.0


@dataclass
class Screenshot:
    """No-op action: agent just wants a fresh observation."""


@dataclass
class Done:
    """Agent signals task completion."""

    success: bool = True
    note: str = ""


# --- DOM element-referencing actions (used by the DOM tool-use agent) --------
# These reference an element by its index in the backend's dom_snapshot(), rather
# than by pixel coordinates. Only web/DOM backends can execute them.


@dataclass
class ClickElement:
    element_id: int


@dataclass
class FillElement:
    element_id: int
    text: str


Action = (
    Click | Move | Scroll | Drag | TypeText | KeyPress | Wait | Screenshot | Done
    | ClickElement | FillElement
)


# --- Coordinate scaling ------------------------------------------------------


def _scale(x: int, y: int, model_size: tuple[int, int], vm_size: tuple[int, int]) -> tuple[int, int]:
    mw, mh = model_size
    vw, vh = vm_size
    if mw <= 0 or mh <= 0 or (mw, mh) == (vw, vh):
        return int(x), int(y)
    return round(x * vw / mw), round(y * vh / mh)


# --- pyautogui codegen -------------------------------------------------------

# Common aliases -> pyautogui key names. pyautogui accepts most names directly;
# this normalizes the few that differ between vendors.
_KEY_ALIASES = {
    "return": "enter",
    "esc": "escape",
    "del": "delete",
    "ctrl": "ctrl",
    "control": "ctrl",
    "cmd": "command",
    "super": "win",
    "meta": "command",
    "option": "alt",
    "pgdn": "pagedown",
    "pgup": "pageup",
}

_PYAUTOGUI_HEADER = (
    "import pyautogui, time\n"
    "pyautogui.FAILSAFE = False\n"
)


def _norm_key(k: str) -> str:
    return _KEY_ALIASES.get(k.strip().lower(), k.strip().lower())


def _py_literal(s: str) -> str:
    """Safe single-quoted Python literal for arbitrary text."""
    return repr(s)


def to_pyautogui(
    action: Action,
    model_size: tuple[int, int],
    vm_size: tuple[int, int],
) -> str | None:
    """Render an action to a pyautogui snippet (string) to run on the VM.

    Returns None for actions with no VM effect (Screenshot, Done) — the caller
    handles those in the loop. Coordinates are scaled model_size -> vm_size.
    """
    body: list[str] = []

    if isinstance(action, Click):
        x, y = _scale(action.x, action.y, model_size, vm_size)
        body.append(
            f"pyautogui.click(x={x}, y={y}, clicks={action.clicks}, "
            f"interval=0.1, button={_py_literal(action.button)})"
        )
    elif isinstance(action, Move):
        x, y = _scale(action.x, action.y, model_size, vm_size)
        body.append(f"pyautogui.moveTo({x}, {y})")
    elif isinstance(action, Scroll):
        x, y = _scale(action.x, action.y, model_size, vm_size)
        body.append(f"pyautogui.moveTo({x}, {y})")
        if action.dy:
            # pyautogui.scroll: positive = up, so negate dy (positive dy = down).
            body.append(f"pyautogui.scroll({-int(action.dy)})")
        if action.dx:
            body.append(f"pyautogui.hscroll({int(action.dx)})")
    elif isinstance(action, Drag):
        x1, y1 = _scale(action.x1, action.y1, model_size, vm_size)
        x2, y2 = _scale(action.x2, action.y2, model_size, vm_size)
        body.append(f"pyautogui.moveTo({x1}, {y1})")
        body.append(f"pyautogui.dragTo({x2}, {y2}, duration=0.4, button='left')")
    elif isinstance(action, TypeText):
        body.append(f"pyautogui.write({_py_literal(action.text)}, interval=0.02)")
    elif isinstance(action, KeyPress):
        keys = [_norm_key(k) for k in action.keys]
        if len(keys) == 1:
            body.append(f"pyautogui.press({_py_literal(keys[0])})")
        elif len(keys) > 1:
            args = ", ".join(_py_literal(k) for k in keys)
            body.append(f"pyautogui.hotkey({args})")
    elif isinstance(action, Wait):
        body.append(f"time.sleep({float(action.seconds)})")
    elif isinstance(action, (Screenshot, Done)):
        return None
    else:
        raise TypeError(f"Unknown action type: {type(action).__name__}")

    return _PYAUTOGUI_HEADER + "\n".join(body) + "\n"


def describe(action: Action) -> str:
    """Short human/log description of an action."""
    return f"{type(action).__name__}({action!r})"
