"""Parse the reward.py output contract.

reward.py prints diagnostics then a final `REWARD: X.X` line (float 0.0-1.0).
We take the LAST match in case multiple scores are printed. Mirrors the regex in
scripts/local/local_verify.py so the two stay consistent.
"""
from __future__ import annotations

import re

_REWARD_RE = re.compile(r"REWARD:\s*([0-9]*\.?[0-9]+)")


def parse_reward(stdout: str) -> float | None:
    """Return the last REWARD score in stdout, or None if absent/malformed."""
    if not stdout:
        return None
    matches = _REWARD_RE.findall(stdout)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except ValueError:
        return None
