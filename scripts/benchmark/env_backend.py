"""Environment backends the rollout engine drives.

The rollout loop is backend-agnostic: it only needs reset / screenshot /
exec_action / score / teardown. Two implementations:

  VMBackend   — real OSWorld VM via utils.env.Env. Provisions a VM, uploads +
                runs initial_setup.py, launches the app, executes pyautogui
                snippets, runs reward.py. Needs ~/OSWorld-RL + Aliyun creds.
                (Wired against the Env API; live-VM validation pending install.)

  FakeBackend — in-memory, no VM/model. Returns canned screenshots, records the
                action snippets it was asked to run, and returns a scripted reward.
                Used to validate the full pipeline end-to-end.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from .actions import Action, describe, to_pyautogui
from .rewards import parse_reward
from .tasks import Task

# Reward judge that must accompany reward.py onto the VM (locked-down judge).
_REPO = Path(__file__).resolve().parents[2]
_REWARD_JUDGE = _REPO / "utils" / "reward_judge.py"

_BASE_URL_RE = re.compile(r"BASE_URL\s*=\s*['\"](https?://[^'\"]+)['\"]")


class EnvBackend(Protocol):
    def reset(self, task: Task) -> tuple[int, int]:
        """Provision + apply initial_setup + launch app. Returns VM screen (w, h)."""

    def screenshot(self) -> bytes | None: ...

    def exec_action(self, action: Action, model_size: tuple[int, int]) -> None:
        """Execute one action against the environment."""

    def score(self, task: Task) -> float | None:
        """Run reward.py on the VM and return the parsed REWARD."""

    def teardown(self) -> None: ...


# --- Real VM backend --------------------------------------------------------

# Wrap a pyautogui snippet so it runs against the VM display.
_DISPLAY_PREAMBLE = "import os\nos.environ.setdefault('DISPLAY', ':0')\n"


class VMBackend:
    """Drives a real OSWorld VM. One VM per rollout (create -> use -> delete).

    Pooling/snapshot reuse is a future optimization; the create/delete contract
    keeps each rollout hermetic, matching the pipeline's dual-env isolation.
    """

    def __init__(self, keep_vm: bool = False):
        self.keep_vm = keep_vm
        self._env = None
        self._screen = (1280, 800)

    def reset(self, task: Task) -> tuple[int, int]:
        from utils.env import Env  # lazy: avoids importing VM deps in tests

        self._env = Env.create(task_id=f"bench_{task.task_id}")
        env = self._env

        # 1. Apply initial state. initial_setup.py is uploaded and run on the VM.
        env.upload(str(task.initial_setup), "/home/user/initial_setup.py")
        env.upload(str(_REWARD_JUDGE), "/home/user/reward_judge.py")
        res = env.run_python("/home/user/initial_setup.py")
        if isinstance(res, dict) and res.get("returncode", 0) not in (0, None):
            raise RuntimeError(f"initial_setup failed: {res.get('error') or res.get('output')}")

        # 2. Screen size for coordinate scaling.
        size = env.get_screen_size() or {}
        self._screen = (size.get("width", 1280), size.get("height", 800))

        # 3. Launch the app the task needs.
        self._launch_app(task)
        return self._screen

    def _launch_app(self, task: Task) -> None:
        if task.is_web:
            # Web mocks: read the sid initial_setup minted, open Chrome at ?sid=.
            base = self._detect_base_url(task)
            sid = self._read_sid()
            url = f"{base}/?sid={sid}" if base else None
            if url:
                self._env.launch(f"google-chrome --start-maximized --no-first-run {url}")
        else:
            # Desktop: launch hint is domain-specific (see .claude/skills/<domain>).
            # Best-effort generic launch by app_type; refine per-domain as needed.
            self._env.launch(task.app_type.replace("_", "-"))

    def _detect_base_url(self, task: Task) -> str | None:
        m = _BASE_URL_RE.search(task.reward.read_text())
        return m.group(1) if m else None

    def _read_sid(self) -> str:
        res = self._env.execute("cat /tmp/task_web_sid")
        return (res.get("output") or "").strip() if isinstance(res, dict) else ""

    @property
    def screen_size(self) -> tuple[int, int]:
        return self._screen

    def screenshot(self) -> bytes | None:
        return self._env.screenshot() if self._env else None

    def exec_action(self, action: Action, model_size: tuple[int, int]) -> None:
        snippet = to_pyautogui(action, model_size or self._screen, self._screen)
        if snippet is not None:
            self._env.run_python(_DISPLAY_PREAMBLE + snippet)

    def score(self, task: Task) -> float | None:
        self._env.upload(str(task.reward), "/home/user/reward.py")
        res = self._env.run_python("/home/user/reward.py")
        out = res.get("output", "") if isinstance(res, dict) else ""
        return parse_reward(out)

    def teardown(self) -> None:
        if self._env is None:
            return
        try:
            if not self.keep_vm and self._env.config.instance_id:
                cfg = Path("/tmp") / f"bench_{self._env.config.instance_id}.json"
                self._env.save_config(cfg)
                from utils.env import Env

                Env.delete_instance(cfg)
        finally:
            self._env.close()
            self._env = None


# --- Fake backend (for tests / pipeline validation) ------------------------


class FakeBackend:
    """No VM, no model. Records executed snippets; returns a scripted reward.

    reward_for: callable(task) -> float used as the score; or a fixed float.
    """

    def __init__(self, reward_for, screen=(1280, 800)):
        self._reward_for = reward_for
        self._screen = screen
        self.executed: list[str] = []
        self.reset_count = 0
        self.teardown_count = 0

    def reset(self, task: Task) -> tuple[int, int]:
        self.reset_count += 1
        self.executed = []
        return self._screen

    @property
    def screen_size(self) -> tuple[int, int]:
        return self._screen

    def screenshot(self) -> bytes | None:
        # Minimal valid 1x1 PNG.
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
            b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

    def exec_action(self, action: Action, model_size: tuple[int, int] = (0, 0)) -> None:
        self.executed.append(describe(action))

    def score(self, task: Task) -> float | None:
        return self._reward_for(task) if callable(self._reward_for) else self._reward_for

    def teardown(self) -> None:
        self.teardown_count += 1
