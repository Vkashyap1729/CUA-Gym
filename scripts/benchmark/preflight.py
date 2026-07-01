"""Preflight: does the harness have everything it needs to run a REAL benchmark?

Checks the required data + deps + creds and prints a readiness table, split by
what each execution path needs:

  ALWAYS      verified tasks in output/final, API keys
  WEB path    playwright + chromium, npm + hub mocks, .venv-local   (local, no VM)
  VM  path    ~/OSWorld-RL + Aliyun creds                           (desktop tasks)
  MODELS      anthropic / openai SDKs (+ computer-use access, checked at run time)

Exit 0 if the WEB path is fully ready (enough to benchmark all mock_websites tasks).

  python scripts/benchmark/preflight.py
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark.tasks import load_tasks  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def _has_module(mod: str, python: Path | None = None) -> bool:
    if python and python.exists():
        import subprocess

        r = subprocess.run([str(python), "-c", f"import {mod}"], capture_output=True)
        return r.returncode == 0
    return importlib.util.find_spec(mod) is not None


def _env_key(name: str) -> bool:
    if os.environ.get(name):
        return True
    envf = REPO / ".env"
    if envf.exists():
        m = re.search(rf"^{name}=(.+)$", envf.read_text(), re.M)
        return bool(m and m.group(1).strip())
    return False


def main() -> int:
    venv = REPO / ".venv-local" / "bin" / "python"
    tasks = load_tasks("output/final")
    web = [t for t in tasks if t.is_web]
    from collections import Counter

    dist = Counter(t.app_type for t in tasks)

    rows = []
    # ALWAYS
    rows.append(("data", "verified tasks in output/final", len(tasks) > 0, f"{len(tasks)} tasks {dict(dist)}"))
    rows.append(("data", "web (mock_websites) tasks", len(web) > 0, f"{len(web)} runnable locally"))
    rows.append(("creds", "ANTHROPIC_API_KEY", _env_key("ANTHROPIC_API_KEY"), ""))
    rows.append(("creds", "OPENAI_API_KEY", _env_key("OPENAI_API_KEY"), ""))
    # WEB path
    rows.append(("web", ".venv-local", venv.exists(), str(venv)))
    rows.append(("web", "playwright (.venv-local)", _has_module("playwright", venv), "pip install playwright"))
    def _chromium_present() -> bool:
        for base in ("Library/Caches/ms-playwright", ".cache/ms-playwright"):
            d = Path.home() / base
            if d.exists() and any(p.name.startswith("chromium") for p in d.iterdir()):
                return True
        return False

    chromium_ok = _chromium_present()
    rows.append(("web", "chromium browser", chromium_ok, "playwright install chromium"))
    rows.append(("web", "npm", shutil.which("npm") is not None, ""))
    rows.append(("web", "hub mocks (submodule)", (REPO / "hub" / "websites").exists(), "git submodule update --init"))
    # MODELS
    rows.append(("models", "anthropic SDK (.venv-local)", _has_module("anthropic", venv), "pip install anthropic"))
    rows.append(("models", "openai SDK (.venv-local)", _has_module("openai", venv), "pip install openai"))
    # VM path
    rows.append(("vm", "~/OSWorld-RL", (Path.home() / "OSWorld-RL").exists(), "needed only for desktop tasks"))
    rows.append(("vm", "ALIYUN_ACCESS_KEY_ID", _env_key("ALIYUN_ACCESS_KEY_ID"), "needed only for desktop tasks"))

    print(f"{'GROUP':7} {'CHECK':34} STATUS  NOTE")
    print("-" * 78)
    for grp, name, ok, note in rows:
        print(f"{grp:7} {name:34} {'✓ ok ' if ok else '✗ MISS'}  {note}")

    web_ready = all(ok for grp, _, ok, _ in rows if grp in ("data", "web"))
    models_ready = any(ok for grp, n, ok, _ in rows if grp == "models")
    print("-" * 78)
    print(f"WEB path ready (can benchmark web tasks locally): {web_ready}")
    print(f"At least one model SDK present: {models_ready}")
    print("Computer-use API ACCESS is verified at run time (1 rollout), not here.")
    return 0 if web_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
