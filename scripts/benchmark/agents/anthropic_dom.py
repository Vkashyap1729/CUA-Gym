"""Anthropic (Claude) DOM tool-use agent.

Same design as dom_tooluse.DOMToolUseAgent but using Claude's tool-use API instead
of OpenAI's. Used because claude-opus-4-8/4.7 do NOT expose the computer-use (GUI)
tool — so we benchmark them via the identical DOM/element tool-use interface as
gpt-5.5, which also makes the comparison apples-to-apples.
"""
from __future__ import annotations

import json

from ..actions import Done
from .base import CUAAgent
from .dom_tooluse import _SYSTEM, _fmt, _map

# Claude-format tool schemas (same semantics as the OpenAI ones in dom_tooluse).
_TOOLS = [
    {"name": "click", "description": "Click an interactive element by its id.",
     "input_schema": {"type": "object", "properties": {"element_id": {"type": "integer"}},
                      "required": ["element_id"]}},
    {"name": "type", "description": "Type text into an input/textarea element by id.",
     "input_schema": {"type": "object", "properties": {
         "element_id": {"type": "integer"}, "text": {"type": "string"}},
         "required": ["element_id", "text"]}},
    {"name": "press", "description": "Press a key or chord, e.g. 'Enter' or 'Control+A'.",
     "input_schema": {"type": "object", "properties": {"keys": {"type": "string"}},
                      "required": ["keys"]}},
    {"name": "scroll", "description": "Scroll the page up or down.",
     "input_schema": {"type": "object", "properties": {
         "direction": {"type": "string", "enum": ["up", "down"]}}, "required": ["direction"]}},
    {"name": "done", "description": "Call when the task is complete.",
     "input_schema": {"type": "object", "properties": {}}},
]


class AnthropicDOMToolUse(CUAAgent):
    def __init__(self, model: str, name: str | None = None, max_tokens: int = 1024):
        super().__init__(name=name or model)
        self.model = model
        self.max_tokens = max_tokens
        self._client = None
        self._messages: list[dict] = []
        self._instruction = ""
        self._pending: list[str] = []  # tool_use ids awaiting tool_result

    def _ensure_client(self):
        if self._client is None:
            from anthropic import Anthropic

            self._client = Anthropic()
        return self._client

    def reset(self, instruction: str, screen_size: tuple[int, int]) -> None:
        self.model_size = screen_size
        self._instruction = instruction
        self._messages = []
        self._pending = []

    def observe(self, backend):
        return backend.dom_snapshot()

    def predict(self, observation) -> list:
        client = self._ensure_client()
        dom_text = "Interactive elements:\n" + _fmt(observation or [])

        if not self._messages:
            self._messages.append({"role": "user", "content": f"TASK: {self._instruction}\n\n{dom_text}"})
        else:
            # answer the prior tool_use blocks with tool_result carrying the new DOM
            self._messages.append({"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": cid, "content": dom_text}
                for cid in self._pending
            ]})
            self._pending = []

        resp = client.messages.create(
            model=self.model, max_tokens=self.max_tokens,
            system=_SYSTEM, tools=_TOOLS, messages=self._messages,
        )
        self._messages.append({"role": "assistant", "content": resp.content})

        actions, text_bits = [], []
        for block in resp.content:
            bt = getattr(block, "type", None)
            if bt == "text":
                text_bits.append(getattr(block, "text", ""))
            elif bt == "tool_use":
                self._pending.append(block.id)
                inp = dict(block.input) if not isinstance(block.input, dict) else block.input
                act = _map(block.name, inp)
                if act is not None:
                    actions.append(act)
        self.last_text = " ".join(text_bits).strip()

        if not any(getattr(b, "type", None) == "tool_use" for b in resp.content):
            actions.append(Done(success=True, note=self.last_text[:200]))
        return actions
