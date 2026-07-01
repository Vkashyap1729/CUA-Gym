"""OpenAI computer-use-preview adapter.

Wraps the `computer-use-preview` model via the Responses API + `computer_use_preview`
tool. Maintains response chaining (previous_response_id), parses `computer_call`
items into unified Actions, and returns each screenshot as a `computer_call_output`.
Safety checks surfaced by the model are acknowledged so the episode can proceed
(benchmark sandbox).

The `openai` SDK is imported lazily. Action parsing is unit-tested against recorded
computer_call shapes in test_pipeline.py.
"""
from __future__ import annotations

import base64

from ..actions import (
    Action,
    Click,
    Done,
    Drag,
    KeyPress,
    Move,
    Screenshot,
    Scroll,
    TypeText,
    Wait,
)
from .base import CUAAgent

_BUTTON = {"left": "left", "right": "right", "middle": "middle", "wheel": "middle"}


def parse_computer_call(action: dict) -> Action | None:
    """Map one OpenAI computer_call action dict to a unified Action."""
    t = action.get("type")
    x, y = int(action.get("x", 0)), int(action.get("y", 0))

    if t == "click":
        return Click(x, y, button=_BUTTON.get(action.get("button", "left"), "left"))
    if t == "double_click":
        return Click(x, y, clicks=2)
    if t == "move":
        return Move(x, y)
    if t == "type":
        return TypeText(action.get("text", ""))
    if t == "keypress":
        keys = action.get("keys") or []
        return KeyPress([str(k).lower() for k in keys])
    if t == "scroll":
        return Scroll(x, y, dx=int(action.get("scroll_x", 0)), dy=int(action.get("scroll_y", 0)))
    if t == "drag":
        path = action.get("path") or []
        if len(path) >= 2:
            return Drag(int(path[0]["x"]), int(path[0]["y"]),
                        int(path[-1]["x"]), int(path[-1]["y"]))
        return None
    if t == "wait":
        return Wait(1.0)
    if t == "screenshot":
        return Screenshot()
    return None


class OpenAICUA(CUAAgent):
    def __init__(self, model: str = "computer-use-preview", name: str | None = None,
                 environment: str = "browser"):
        super().__init__(name=name or model)
        self.model = model
        self.environment = environment
        self._client = None
        self._instruction = ""
        self._prev_response_id: str | None = None
        self._pending_call_id: str | None = None
        self._pending_safety: list = []
        self._first = True

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def reset(self, instruction: str, screen_size: tuple[int, int]) -> None:
        self.model_size = screen_size
        self._instruction = instruction
        self._prev_response_id = None
        self._pending_call_id = None
        self._pending_safety = []
        self._first = True

    def _tool(self) -> dict:
        w, h = self.model_size
        return {
            "type": "computer_use_preview",
            "display_width": w,
            "display_height": h,
            "environment": self.environment,
        }

    def _img_url(self, png: bytes) -> str:
        return "data:image/png;base64," + base64.b64encode(png or b"").decode()

    def predict(self, observation) -> list[Action]:
        screenshot_png = observation  # this adapter observes a screenshot
        client = self._ensure_client()

        if self._first:
            input_items = [{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": self._instruction},
                    {"type": "input_image", "image_url": self._img_url(screenshot_png)},
                ],
            }]
            self._first = False
        else:
            output = {
                "type": "computer_call_output",
                "call_id": self._pending_call_id,
                "output": {"type": "input_image", "image_url": self._img_url(screenshot_png)},
            }
            if self._pending_safety:
                output["acknowledged_safety_checks"] = self._pending_safety
            input_items = [output]

        resp = client.responses.create(
            model=self.model,
            tools=[self._tool()],
            input=input_items,
            previous_response_id=self._prev_response_id,
            truncation="auto",
        )
        self._prev_response_id = resp.id

        actions: list[Action] = []
        calls = [o for o in resp.output if getattr(o, "type", None) == "computer_call"]
        for call in calls:
            self._pending_call_id = call.call_id
            self._pending_safety = getattr(call, "pending_safety_checks", []) or []
            act = parse_computer_call(dict(call.action))
            if act is not None:
                actions.append(act)

        self.last_text = (getattr(resp, "output_text", "") or "").strip()
        if not calls:
            actions.append(Done(success=True, note=self.last_text[:200]))
        return actions
