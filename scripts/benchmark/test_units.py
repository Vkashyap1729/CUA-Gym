"""Pure unit tests for the benchmark action + reward layers (no VM, no model).

Run:  python scripts/benchmark/test_units.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.benchmark import actions as A  # noqa: E402
from scripts.benchmark.rewards import parse_reward  # noqa: E402

_failures = []


def check(name: str, cond: bool, detail: str = ""):
    status = "ok" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f"  {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(name)


def test_parse_reward():
    print("parse_reward:")
    check("simple", parse_reward("REWARD: 1.0") == 1.0)
    check("partial", parse_reward("Score: 0.6/1.0\nREWARD: 0.6") == 0.6)
    check("last_wins", parse_reward("REWARD: 0.2\n...\nREWARD: 0.0") == 0.0)
    check("zero", parse_reward("REWARD: 0.0") == 0.0)
    check("missing", parse_reward("no score here") is None)
    check("empty", parse_reward("") is None)
    check("int_form", parse_reward("REWARD: 1") == 1.0)


def test_pyautogui_codegen():
    print("to_pyautogui:")
    same = (1280, 800)
    # Click, no scaling
    snip = A.to_pyautogui(A.Click(100, 200), same, same)
    check("click_coords", "x=100, y=200" in snip, snip)
    check("click_button", "button='left'" in snip)
    # Double click
    dbl = A.to_pyautogui(A.Click(10, 10, clicks=2), same, same)
    check("double_click", "clicks=2" in dbl)
    # Scaling: model 1280x800 -> vm 2560x1600 doubles coords
    scaled = A.to_pyautogui(A.Click(100, 200), (1280, 800), (2560, 1600))
    check("scaled_coords", "x=200, y=400" in scaled, scaled)
    # Type
    typ = A.to_pyautogui(A.TypeText("hi there"), same, same)
    check("type_text", "pyautogui.write('hi there'" in typ, typ)
    # Type with quotes is safely escaped (uses repr)
    q = A.to_pyautogui(A.TypeText("it's \"ok\""), same, same)
    check("type_quotes_safe", "pyautogui.write(" in q and "\n" not in q.split("write(", 1)[1].split(")", 1)[0])
    # Single key
    k1 = A.to_pyautogui(A.KeyPress(["enter"]), same, same)
    check("key_single", "pyautogui.press('enter')" in k1, k1)
    # Key alias return->enter
    k2 = A.to_pyautogui(A.KeyPress(["Return"]), same, same)
    check("key_alias", "pyautogui.press('enter')" in k2, k2)
    # Chord
    k3 = A.to_pyautogui(A.KeyPress(["ctrl", "c"]), same, same)
    check("key_chord", "pyautogui.hotkey('ctrl', 'c')" in k3, k3)
    # Scroll down -> negative pyautogui.scroll
    sc = A.to_pyautogui(A.Scroll(50, 50, dy=3), same, same)
    check("scroll_down_negated", "pyautogui.scroll(-3)" in sc, sc)
    # Drag
    dr = A.to_pyautogui(A.Drag(0, 0, 100, 100), same, same)
    check("drag", "dragTo(100, 100" in dr, dr)
    # Wait
    w = A.to_pyautogui(A.Wait(2.5), same, same)
    check("wait", "time.sleep(2.5)" in w, w)
    # No-op actions return None
    check("screenshot_none", A.to_pyautogui(A.Screenshot(), same, same) is None)
    check("done_none", A.to_pyautogui(A.Done(), same, same) is None)
    # All snippets carry the header
    check("header_present", A.to_pyautogui(A.Click(1, 1), same, same).startswith("import pyautogui"))


def main():
    test_parse_reward()
    test_pyautogui_codegen()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} -> {_failures}")
        return 1
    print("All unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
