"""DOM / accessibility tool-use agent (fallback for models without computer-use).

Instead of screenshots + pixel clicks, this agent observes the page's list of
interactive elements (from PlaywrightWebBackend.dom_snapshot()) and acts through
function/tool calls that reference elements by index. Works with any OpenAI model
that supports tool-calling (e.g. gpt-5.5) — no computer-use beta required.

Tools -> unified actions:
  click(element_id)        -> ClickElement
  type(element_id, text)   -> FillElement
  press(keys)              -> KeyPress   (e.g. "Enter", "Control+A")
  scroll(direction)        -> Scroll
  done()                   -> Done
"""
from __future__ import annotations

import json

from ..actions import ClickElement, Done, FillElement, KeyPress, Scroll
from .base import CUAAgent

_TOOLS = [
    {"type": "function", "function": {
        "name": "click", "description": "Click an interactive element by its id.",
        "parameters": {"type": "object", "properties": {"element_id": {"type": "integer"}},
                       "required": ["element_id"]}}},
    {"type": "function", "function": {
        "name": "type", "description": "Type text into an input/textarea element by id.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "integer"}, "text": {"type": "string"}},
            "required": ["element_id", "text"]}}},
    {"type": "function", "function": {
        "name": "press", "description": "Press a key or chord, e.g. 'Enter' or 'Control+A'.",
        "parameters": {"type": "object", "properties": {"keys": {"type": "string"}},
                       "required": ["keys"]}}},
    {"type": "function", "function": {
        "name": "scroll", "description": "Scroll the page up or down.",
        "parameters": {"type": "object", "properties": {
            "direction": {"type": "string", "enum": ["up", "down"]}}, "required": ["direction"]}}},
    {"type": "function", "function": {
        "name": "done", "description": "Call when the task is complete.",
        "parameters": {"type": "object", "properties": {}}}},
]

_SYSTEM = (
    "You are a web agent completing a task by acting on a live web app. Each turn "
    "you get the list of visible interactive elements (id, tag, label). Use the "
    "tools to click/type/press/scroll. Reference elements by their id. Do the FULL "
    "task, then call done(). Do not call done() until the task is actually complete. "
    "Prefer the minimal set of actions; avoid side effects the task didn't ask for."
)

_MAX_ELS = 120


def _fmt(elements: list[dict]) -> str:
    lines = []
    for e in elements[:_MAX_ELS]:
        lbl = e.get("label") or ""
        val = f" value='{e['value']}'" if e.get("value") else ""
        lines.append(f"[{e['id']}] <{e['tag']}> {lbl!r}{val}")
    if not lines:
        return "(no interactive elements visible)"
    return "\n".join(lines)


def _map(name: str, args: dict):
    if name == "click":
        return ClickElement(int(args["element_id"]))
    if name == "type":
        return FillElement(int(args["element_id"]), str(args.get("text", "")))
    if name == "press":
        return KeyPress(str(args.get("keys", "")).split("+"))
    if name == "scroll":
        return Scroll(640, 400, dy=3 if args.get("direction") == "down" else -3)
    if name == "done":
        return Done(success=True)
    return None


class DOMToolUseAgent(CUAAgent):
    def __init__(self, model: str = "gpt-5.5", name: str | None = None):
        super().__init__(name=name or model)
        self.model = model
        self._client = None
        self._messages: list[dict] = []
        self._pending: list[str] = []  # tool_call_ids awaiting a tool response

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client

    def reset(self, instruction: str, screen_size: tuple[int, int]) -> None:
        self.model_size = screen_size
        self._messages = [{"role": "system", "content": _SYSTEM},
                          {"role": "user", "content": f"TASK: {instruction}"}]
        self._pending = []

    def observe(self, backend):
        return backend.dom_snapshot()

    def predict(self, observation) -> list:
        client = self._ensure_client()
        dom_text = "Interactive elements:\n" + _fmt(observation or [])

        if self._pending:
            # respond to each pending tool call with the fresh observation
            for cid in self._pending:
                self._messages.append({"role": "tool", "tool_call_id": cid, "content": dom_text})
            self._pending = []
        else:
            self._messages.append({"role": "user", "content": dom_text})

        resp = client.chat.completions.create(
            model=self.model, messages=self._messages, tools=_TOOLS, tool_choice="auto",
        )
        msg = resp.choices[0].message
        self.last_text = msg.content or ""

        assistant = {"role": "assistant", "content": msg.content or ""}
        actions = []
        if msg.tool_calls:
            assistant["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in msg.tool_calls
            ]
            self._messages.append(assistant)
            for tc in msg.tool_calls:
                self._pending.append(tc.id)
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                act = _map(tc.function.name, args)
                if act is not None:
                    actions.append(act)
        else:
            self._messages.append(assistant)
            actions.append(Done(success=True, note=self.last_text[:200]))
        return actions
