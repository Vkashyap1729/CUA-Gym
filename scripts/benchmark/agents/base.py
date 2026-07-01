"""Agent interface for the benchmark panel.

A CUAAgent observes a screenshot + the task instruction + the running history and
returns the next batch of actions. Concrete adapters (Phase 2) wrap the Anthropic
computer_20250124 tool and the OpenAI computer-use-preview model. The
ScriptedAgent below needs no model and is used to validate the rollout loop.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..actions import Action, Done


@dataclass
class Step:
    """One turn of the rollout, recorded in the trace."""

    index: int
    actions: list[Action] = field(default_factory=list)
    model_text: str = ""  # any reasoning/text the model emitted this turn


class CUAAgent(ABC):
    """Base class for a benchmarked computer-use model.

    name        : stable identifier used in output paths/leaderboard
    model_size  : (w, h) the agent reasons in == the screenshot it is given.
                  Adapters set this from the VM screen size at reset().
    """

    name: str = "base"

    def __init__(self, name: str | None = None):
        if name:
            self.name = name
        self.model_size: tuple[int, int] = (0, 0)
        # Reasoning/text the model emitted on the most recent predict() — recorded
        # into the trajectory so the Deep Dive view can show *why* it acted.
        self.last_text: str = ""

    @abstractmethod
    def reset(self, instruction: str, screen_size: tuple[int, int]) -> None:
        """Start a new episode. Clears history; records the VM screen size."""

    def observe(self, backend):
        """Pull the observation this agent type needs from the backend.

        Default: a screenshot (for pixel/computer-use agents). The DOM tool-use
        agent overrides this to return the backend's dom_snapshot() instead.
        """
        return backend.screenshot()

    @abstractmethod
    def predict(self, observation) -> list[Action]:
        """Given the latest observation, return the next actions to execute.

        Return a list ending in Done() to terminate the episode. An empty list
        is treated as a no-op (the loop will re-observe).
        """


class ScriptedAgent(CUAAgent):
    """Replays a fixed action sequence — no model. Validates the rollout loop.

    Each predict() pops the next batch from the script; when exhausted it returns
    [Done()]. Useful as a control and for unit/integration tests.
    """

    name = "scripted"

    def __init__(self, script: list[list[Action]], name: str = "scripted"):
        super().__init__(name=name)
        self._script = list(script)
        self._i = 0

    def reset(self, instruction: str, screen_size: tuple[int, int]) -> None:
        self.model_size = screen_size
        self._i = 0

    def predict(self, observation) -> list[Action]:
        if self._i >= len(self._script):
            return [Done(success=True, note="script exhausted")]
        batch = self._script[self._i]
        self._i += 1
        return batch
