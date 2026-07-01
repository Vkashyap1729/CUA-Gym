"""The benchmark model panel + factory.

PANEL is the default set of models benchmarked. Model IDs are pinned here in ONE
place — update them as new computer-use models ship. `build_agent(key)` constructs
a fresh agent per rollout (agents are stateful across an episode).
"""
from __future__ import annotations

from .anthropic_cua import AnthropicCUA
from .anthropic_dom import AnthropicDOMToolUse
from .base import CUAAgent
from .dom_tooluse import DOMToolUseAgent
from .openai_cua import OpenAICUA

# key -> (vendor, model_id). The key is the stable name used in output paths.
#
# Frontier panel (matches the paper's reference models). VERIFY these exact model
# IDs against your account before a live run — a wrong ID fails at call time:
#   * Opus 4.8 / 4.7 support the Anthropic computer-use tool (computer_20250124).
#   * OpenAI computer-use runs through the `computer_use_preview` tool. That tool is
#     tied to the `computer-use-preview` model; a general model like GPT-5.5 may NOT
#     accept it. If GPT-5.5 rejects the tool, either keep `computer-use-preview` for
#     the OpenAI slot or switch GPT-5.5 to the DOM tool-use agent (the chosen fallback).
# All three run via DOM tool-use: opus-4.8/4.7 don't expose the computer-use GUI
# tool, and gpt-5.5 doesn't support computer_use_preview — so a consistent
# element/tool-use interface is both the only working path AND an apples-to-apples
# comparison. (`anthropic`/`openai` computer-use vendors remain for models that DO
# support the GUI tool, e.g. via the VM.)
PANEL: dict[str, tuple[str, str]] = {
    "opus-4.8": ("anthropic_dom", "claude-opus-4-8"),
    "opus-4.7": ("anthropic_dom", "claude-opus-4-7"),
    "gpt-5.5":  ("openai_dom", "gpt-5.5"),
}


def build_agent(key: str) -> CUAAgent:
    if key not in PANEL:
        raise KeyError(f"unknown model {key!r}; panel = {list(PANEL)}")
    vendor, model_id = PANEL[key]
    if vendor == "anthropic":
        return AnthropicCUA(model=model_id, name=key)
    if vendor == "openai":
        return OpenAICUA(model=model_id, name=key)
    if vendor == "openai_dom":
        return DOMToolUseAgent(model=model_id, name=key)
    if vendor == "anthropic_dom":
        return AnthropicDOMToolUse(model=model_id, name=key)
    raise ValueError(f"unknown vendor {vendor!r}")


def panel_keys() -> list[str]:
    return list(PANEL)
