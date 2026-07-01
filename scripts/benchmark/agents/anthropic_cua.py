"""Anthropic computer-use adapter.

Wraps the Claude `computer_20250124` tool. Maintains the message history, parses
`tool_use` blocks named "computer" into the unified Action schema, and feeds each
screenshot back as a `tool_result` image. Coordinates are reported by the model in
the display space we declare (== the VM screen), so model_size == vm screen.

Live validation requires the `anthropic` SDK + computer-use access; the SDK is
imported lazily so the rest of the pipeline imports without it. Tool-call parsing
is unit-tested against recorded block shapes in test_pipeline.py.
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

_BETA = "computer-use-2025-01-24"

# Anthropic computer-tool action name -> our builder.
_CLICK_BUTTON = {
    "left_click": "left",
    "right_click": "right",
    "middle_click": "middle",
}


def parse_tool_input(name: str, inp: dict) -> Action | None:
    """Map one Claude computer tool_use input to a unified Action (or None)."""
    if name != "computer":
        return None
    a = inp.get("action")
    coord = inp.get("coordinate") or [0, 0]
    x, y = int(coord[0]), int(coord[1])

    if a == "screenshot":
        return Screenshot()
    if a == "wait":
        return Wait(float(inp.get("duration", 1)))
    if a == "cursor_position":
        return Screenshot()  # benign no-op observation
    if a == "mouse_move":
        return Move(x, y)
    if a in _CLICK_BUTTON:
        return Click(x, y, button=_CLICK_BUTTON[a])
    if a == "double_click":
        return Click(x, y, clicks=2)
    if a == "triple_click":
        return Click(x, y, clicks=3)
    if a == "left_click_drag":
        start = inp.get("start_coordinate") or [x, y]
        return Drag(int(start[0]), int(start[1]), x, y)
    if a == "type":
        return TypeText(inp.get("text", ""))
    if a == "key":
        return KeyPress(str(inp.get("text", "")).split("+"))
    if a == "scroll":
        direction = inp.get("scroll_direction", "down")
        amount = int(inp.get("scroll_amount", 3))
        dy = amount if direction == "down" else -amount if direction == "up" else 0
        dx = amount if direction == "right" else -amount if direction == "left" else 0
        return Scroll(x, y, dx=dx, dy=dy)
    return None


class AnthropicCUA(CUAAgent):
    def __init__(self, model: str, name: str | None = None, max_tokens: int = 1024):
        super().__init__(name=name or model)
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self._messages: list[dict] = []
        self._instruction = ""
        self._pending_tool_use_id: str | None = None

    def _ensure_client(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic()
        return self._client

    def reset(self, instruction: str, screen_size: tuple[int, int]) -> None:
        self.model_size = screen_size
        self._instruction = instruction
        self._messages = []
        self._pending_tool_use_id = None

    def _tool(self) -> dict:
        w, h = self.model_size
        return {
            "type": "computer_20250124",
            "name": "computer",
            "display_width_px": w,
            "display_height_px": h,
            "display_number": 1,
        }

    def predict(self, observation) -> list[Action]:
        screenshot_png = observation  # this adapter observes a screenshot
        client = self._ensure_client()
        img_b64 = base64.b64encode(screenshot_png or b"").decode()
        img_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
        }

        if not self._messages:
            self._messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": self._instruction},
                    img_block,
                ],
            })
        else:
            # Return the prior tool_use's screenshot as a tool_result.
            self._messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": self._pending_tool_use_id,
                    "content": [img_block],
                }],
            })

        resp = client.beta.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tools=[self._tool()],
            messages=self._messages,
            betas=[_BETA],
        )
        self._messages.append({"role": "assistant", "content": resp.content})

        actions: list[Action] = []
        text_bits = []
        for block in resp.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_bits.append(getattr(block, "text", ""))
            elif btype == "tool_use":
                self._pending_tool_use_id = block.id
                act = parse_tool_input(block.name, dict(block.input))
                if act is not None:
                    actions.append(act)

        self.last_text = " ".join(text_bits).strip()
        # No tool call -> the model is done (it answered in text).
        if not any(getattr(b, "type", None) == "tool_use" for b in resp.content):
            actions.append(Done(success=True, note=self.last_text[:200]))
        return actions
