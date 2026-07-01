"""Local browser backend — REAL GUI rollouts for mock_websites tasks, NO Aliyun VM.

Drives a headless Chromium (Playwright) against a locally-hosted mock. Replaces the
OSWorld VM for the 94 web tasks: the model still sees screenshots and emits
clicks/keystrokes, but they hit a local browser instead of a remote VM.

Per rollout:
  1. mint a fresh sid: run the task's (localized) initial_setup.py -> injects state
     into the mock + writes /tmp/task_web_sid  (same mechanism as local_verify.py)
  2. open Chromium at <mock_url>/?sid=<sid>
  3. screenshot -> model -> Playwright mouse/keyboard -> repeat
  4. run the (localized) reward.py -> parse REWARD

CONCURRENCY: uses the shared /tmp/task_web_sid file, so run with concurrency=1
locally (or one sid file per worker). Fine for a local pilot.

Requires: playwright + chromium, a running mock server (see scripts/local/start_mock.sh).
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from .actions import (
    Click,
    ClickElement,
    Drag,
    FillElement,
    KeyPress,
    Move,
    Scroll,
    TypeText,
    Wait,
)
from .rewards import parse_reward
from .tasks import Task

# Interactive elements the DOM tool-use agent can see + act on.
_INTERACTIVE = ("a, button, input, textarea, select, [role=button], [role=link], "
                "[role=checkbox], [role=tab], [role=menuitem], [contenteditable=true]")

_REPO = Path(__file__).resolve().parents[2]
_LOCAL = _REPO / "scripts" / "local"
_SID_FILE = "/tmp/task_web_sid"
_XLANG_RE = re.compile(r"https://cua-gym-[a-z0-9_-]+\.xlang\.ai")

# our key names -> Playwright key names
_PW_KEYS = {
    "enter": "Enter", "return": "Enter", "tab": "Tab", "escape": "Escape", "esc": "Escape",
    "backspace": "Backspace", "delete": "Delete", "space": "Space", "ctrl": "Control",
    "control": "Control", "alt": "Alt", "shift": "Shift", "cmd": "Meta", "meta": "Meta",
    "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
    "pageup": "PageUp", "pagedown": "PageDown", "home": "Home", "end": "End",
}


def _pw_key(k: str) -> str:
    k = k.strip().lower()
    if k in _PW_KEYS:
        return _PW_KEYS[k]
    return k.upper() if len(k) == 1 else k.capitalize()


def _localize(src: str, mock_url: str) -> str:
    return _XLANG_RE.sub(mock_url, src).replace("google-chrome", "true")


class PlaywrightWebBackend:
    def __init__(self, mock_url: str, python: str | None = None,
                 viewport=(1280, 800), headless: bool = True, run_timeout: int = 120):
        self.mock_url = mock_url.rstrip("/")
        self.python = python or str(_REPO / ".venv-local" / "bin" / "python")
        self.viewport = viewport
        self.headless = headless
        self.run_timeout = run_timeout
        self._pw = self._browser = self._ctx = self._page = None
        self._tmp = None
        self._sid = None
        self._els = []  # element handles from the most recent dom_snapshot()

    # --- helpers ---

    def _env(self) -> dict:
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{_LOCAL}{os.pathsep}{_REPO / 'utils'}{os.pathsep}" + env.get("PYTHONPATH", "")
        return env

    def _write_localized(self, task: Task) -> Path:
        d = Path(self._tmp.name)
        for name in ("initial_setup.py", "reward.py"):
            (d / name).write_text(_localize((task.task_dir / name).read_text(), self.mock_url))
        return d

    def _run_script(self, script: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.python, str(script)], capture_output=True, text=True,
            env=self._env(), cwd=str(script.parent), timeout=self.run_timeout,
        )

    # --- backend protocol ---

    def reset(self, task: Task) -> tuple[int, int]:
        from playwright.sync_api import sync_playwright

        self._tmp = tempfile.TemporaryDirectory(prefix="cuagym_web_")
        run_dir = self._write_localized(task)

        # 1. fresh sid + initial state
        if os.path.exists(_SID_FILE):
            os.remove(_SID_FILE)
        cp = self._run_script(run_dir / "initial_setup.py")
        if cp.returncode != 0:
            raise RuntimeError(f"initial_setup failed: {cp.stderr.strip()[:300]}")
        self._sid = Path(_SID_FILE).read_text().strip()

        # 2. browser at the mock, on this sid
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=self.headless)
        self._ctx = self._browser.new_context(
            viewport={"width": self.viewport[0], "height": self.viewport[1]})
        self._page = self._ctx.new_page()
        self._page.goto(f"{self.mock_url}/?sid={self._sid}", wait_until="networkidle")
        return self.viewport

    @property
    def screen_size(self) -> tuple[int, int]:
        return self.viewport

    def screenshot(self) -> bytes | None:
        try:
            return self._page.screenshot()
        except Exception:
            return None

    def dom_snapshot(self) -> list[dict]:
        """Visible interactive elements as [{id, tag, label, value}], refreshed each
        call. Element handles are cached so ClickElement/FillElement can resolve id.
        """
        self._els = []
        out = []
        try:
            handles = self._page.query_selector_all(_INTERACTIVE)
        except Exception:
            return out
        for h in handles:
            try:
                if not h.is_visible():
                    continue
                tag = h.evaluate("e => e.tagName.toLowerCase()")
                label = (h.get_attribute("aria-label") or (h.inner_text() or "").strip()
                         or h.get_attribute("placeholder") or h.get_attribute("title") or "")
                val = h.get_attribute("value") or ""
                idx = len(self._els)
                self._els.append(h)
                out.append({"id": idx, "tag": tag, "label": label.strip()[:100], "value": val[:60]})
            except Exception:
                continue
        return out

    def exec_action(self, action, model_size: tuple[int, int] = (0, 0)) -> None:
        p = self._page
        m = p.mouse
        if isinstance(action, ClickElement):
            if 0 <= action.element_id < len(self._els):
                self._els[action.element_id].click(timeout=5000)
        elif isinstance(action, FillElement):
            if 0 <= action.element_id < len(self._els):
                h = self._els[action.element_id]
                try:
                    h.fill(action.text, timeout=5000)
                except Exception:
                    h.click(timeout=5000)
                    p.keyboard.type(action.text, delay=15)
        elif isinstance(action, Click):
            m.click(action.x, action.y, button=action.button, click_count=action.clicks)
        elif isinstance(action, Move):
            m.move(action.x, action.y)
        elif isinstance(action, Scroll):
            m.move(action.x, action.y)
            p.mouse.wheel(action.dx * 100, action.dy * 100)
        elif isinstance(action, Drag):
            m.move(action.x1, action.y1); m.down()
            m.move(action.x2, action.y2); m.up()
        elif isinstance(action, TypeText):
            p.keyboard.type(action.text, delay=15)
        elif isinstance(action, KeyPress):
            keys = [_pw_key(k) for k in action.keys]
            if len(keys) == 1:
                p.keyboard.press(keys[0])
            elif keys:
                p.keyboard.press("+".join(keys))
        elif isinstance(action, Wait):
            p.wait_for_timeout(action.seconds * 1000)

    def score(self, task: Task) -> float | None:
        cp = self._run_script(Path(self._tmp.name) / "reward.py")
        return parse_reward(cp.stdout)

    def teardown(self) -> None:
        for closer in (
            lambda: self._page and self._page.close(),
            lambda: self._ctx and self._ctx.close(),
            lambda: self._browser and self._browser.close(),
            lambda: self._pw and self._pw.stop(),
            lambda: self._tmp and self._tmp.cleanup(),
        ):
            try:
                closer()
            except Exception:
                pass
        self._page = self._ctx = self._browser = self._pw = self._tmp = None
