"""The rollout engine: run ONE episode of (task, model, seed).

Backend-agnostic and agent-agnostic. Loop:

    reset env (setup + launch)  ->  for step in range(max_steps):
        screenshot -> agent.predict -> [actions] -> exec each on env
        stop on Done or when no actions remain
    -> run reward.py -> classify outcome -> record trace

Returns a (RolloutResult, trace) pair. The trace is the full step-by-step record
written to rollouts/<task>__<model>__<seed>.json.
"""
from __future__ import annotations

import base64
import time
import traceback

from .actions import Done, Screenshot, describe
from .agents.base import CUAAgent
from .metrics import RolloutResult, classify_outcome


def _as_data_uri(png: bytes | None) -> str | None:
    if not png:
        return None
    return "data:image/png;base64," + base64.b64encode(png).decode()


def run_episode(
    task,
    agent: CUAAgent,
    backend,
    seed: int = 0,
    max_steps: int = 25,
    time_budget_s: float = 600.0,
    record_screens: bool = True,
    clock=time.monotonic,
) -> tuple[RolloutResult, dict]:
    """Run one episode. `clock` is injectable so tests can simulate timeouts."""
    t0 = clock()
    trace = {
        "task_id": task.task_id,
        "model": agent.name,
        "seed": seed,
        "app_type": task.app_type,
        "instruction": task.instruction,
        "max_steps": max_steps,
        "steps": [],
    }

    reward = None
    n_actions = 0
    step = 0
    terminated = False
    truncated = False
    errored = False
    timed_out = False
    err_msg = None

    try:
        vm_size = backend.reset(task)
        agent.reset(task.instruction, vm_size)

        while step < max_steps:
            if clock() - t0 > time_budget_s:
                timed_out = True
                break

            obs = agent.observe(backend)
            actions = agent.predict(obs) or []

            step_rec = {
                "index": step,
                "actions": [describe(a) for a in actions],
                "reasoning": getattr(agent, "last_text", "") or "",
            }
            if record_screens:
                # Reuse the observation if it's already a screenshot; else grab one.
                shot = obs if isinstance(obs, (bytes, bytearray)) else backend.screenshot()
                step_rec["screenshot"] = _as_data_uri(shot)
            trace["steps"].append(step_rec)

            done = False
            for action in actions:
                if isinstance(action, Done):
                    done = True
                    terminated = True
                    break
                if isinstance(action, Screenshot):
                    continue  # loop re-observes next iteration
                # Backends render the action themselves (VM -> pyautogui,
                # browser -> Playwright), scaling from the model's display space.
                backend.exec_action(action, agent.model_size or vm_size)
                n_actions += 1
            step += 1
            if done:
                break
        else:
            truncated = True  # exhausted max_steps without Done

        reward = backend.score(task)

    except Exception as exc:  # noqa: BLE001 — any failure is an ERROR outcome
        errored = True
        err_msg = f"{type(exc).__name__}: {exc}"
        trace["traceback"] = traceback.format_exc()
    finally:
        try:
            backend.teardown()
        except Exception:  # teardown must never mask the result
            pass

    outcome = classify_outcome(
        reward, terminated=terminated, truncated=truncated,
        errored=errored, timed_out=timed_out,
    )
    result = RolloutResult(
        task_id=task.task_id,
        model=agent.name,
        seed=seed,
        reward=reward,
        outcome=outcome,
        steps=step,
        n_actions=n_actions,
        duration_s=round(clock() - t0, 2),
        error=err_msg,
        app_type=task.app_type,
    )
    trace["result"] = result.to_dict()
    return result, trace
