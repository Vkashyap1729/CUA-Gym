"""
Local web-only CUA-Gym pipeline (NO VM, NO Aliyun).

Runs the adversarial co-generation loop on your machine for mock-website tasks
(Gmail by default). Per task spec it:

  1. setup-gen  (claude -p) -> writes initial_setup.py + golden_patch.py
  2. reward-gen (claude -p, information barrier) -> writes reward.py
  3. local_verify -> runs the dual-env check against the locally-hosted mock
  4. on FAIL, feeds a REVIEW back and retries (<= MAX_ROUNDS)
  5. on PASS, exports output/final/<id>/ in CUA-Gym-native format

Prereqs (see scripts/local/README.md):
  - the mock running locally:  cd hub/websites/gmail_mock && npm run dev -- --port 5173
  - .venv-local with requests+openai
  - claude CLI authenticated
  - OPENAI_API_KEY in env (for reward.py LLM-judge tasks; CUA_GYM_JUDGE_MODEL optional)

Usage:
  python scripts/local/run_local_pipeline.py <task_specs.json> \
      [--mock-url http://localhost:5173] [--app gmail] [--max-rounds 5] \
      [--only gmail_001] [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
from local_verify import verify_task  # noqa: E402

VENV_PY = str(REPO / ".venv-local" / "bin" / "python")
ADV = REPO / "output" / "adversarial"
SANDBOX = REPO / "output" / "reward_sandbox"
FINAL = REPO / "output" / "final"
STATUS_FILE = REPO / "output" / "local_batch_status.json"
MAX_ROUNDS = 5

SCHEMA_REL = ".claude/skills/mock_websites/schemas/{app}_mock.md"
SKILL_REL = ".claude/skills/mock_websites/SKILL.md"
# Host uses HYPHENS, not underscores (underscores are invalid DNS labels): the public
# URL pattern is cua-gym-<name-with-hyphens>.xlang.ai. Localized to the mock at verify time.
def base_url_for(app: str) -> str:
    return "https://cua-gym-" + app.replace("_", "-") + ".xlang.ai"

SETUP_PROMPT = """You are the setup-gen agent for CUA-Gym (domain: mock_websites, mock: {app}).

FIRST read these for the exact state schema and script templates:
- {skill}
- {schema}

TASK INSTRUCTION:
{instruction}

GROUND-TRUTH CONTEXT (describes the INITIAL state to build AND the expected END state):
{context}

Write EXACTLY two files into the current directory ({task_dir}):

1) initial_setup.py — builds the INITIAL inbox described in the context.
   - generate a uuid sid, write it to /tmp/task_web_sid
   - POST action:"set" with the FULL state (ALL required top-level keys from the schema:
     user, emails, labels, drafts). Include every distractor email the context names.
   - the initial state MUST represent the task as NOT yet done (so a fresh reward = 0.0)
   - launch chrome per the template (it is a harmless no-op locally)
   - use BASE_URL = '{base_url}'

2) golden_patch.py — produces the COMPLETED state.
   - read sid from /tmp/task_web_sid
   - GET /go, deep-copy initial_state, apply ONLY the changes the task requires
     (per the context's expected end state — touch nothing else)
   - POST action:"set_current" (NEVER "set")
   - use BASE_URL = '{base_url}'

Follow the SKILL.md templates exactly. Do not write any other files. When done, print DONE.
"""

REWARD_PROMPT = """You are the reward-gen agent for CUA-Gym (domain: mock_websites, mock: {app}).

INFORMATION BARRIER: you must NOT read initial_setup.py or golden_patch.py. Work from the
task description alone. (They are not in this directory anyway.)

FIRST read the state schema:
- {schema}

TASK INSTRUCTION:
{instruction}

GROUND-TRUTH CONTEXT (initial state + expected end state):
{context}

Write EXACTLY one file into the current directory ({task_dir}): reward.py

reward.py must:
  - read sid from /tmp/task_web_sid
  - GET '{base_url}/go?sid=' + sid  (use BASE_URL = '{base_url}')
  - inspect current_state (and state_diff) and score ONLY the task-introduced change
  - be progressive (0.0-1.0) and print 'REWARD: X.X' as the LAST line
  - score 0.0 on the initial (not-done) state and 1.0 on the fully-completed state
  - penalize over-action: distractor emails named in the context must be unchanged
  - for subjective/body-content checks (e.g. a sent reply's wording), use
    `from reward_judge import call_llm_judge` for at most 40% of the score, and put a
    `# JUSTIFICATION:` comment above each call. Most criteria should be exact state checks.

FORBIDDEN: subprocess, `from openai import ...`, hardcoded `return 1.0`, file-existence scoring.
Do not write any other files. When done, print DONE.
"""

REVIEW_SUFFIX = """

--- PREVIOUS ROUND FAILED — fix and rewrite your file(s) ---
{review}
"""


def load_specs(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict) and "tasks" in data:
        data = data["tasks"]
    if not isinstance(data, list):
        data = [data]
    out = []
    for i, t in enumerate(data):
        out.append({
            "id": t.get("task_id") or t.get("id") or f"task_{i:03d}",
            "instruction": t.get("task_instruction") or t.get("instruction") or "",
            "context": t.get("context", ""),
            "app": t.get("app") or "gmail",
        })
    return out


def load_dotenv(path: Path = REPO / ".env") -> None:
    """Load KEY=VALUE pairs from .env into os.environ, OVERRIDING the shell.

    A stale/invalid ANTHROPIC_API_KEY exported in the user's shell profile would
    otherwise win and break headless `claude`. Loading .env (override) ensures the
    valid key from .env is used, and gives reward.py its OPENAI_API_KEY.
    """
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ[key.strip()] = val.strip().strip('"').strip("'")


def run_agent(role: str, prompt: str, cwd: Path, timeout: int = 1800) -> subprocess.CompletedProcess:
    # Plain `claude -p` (default agent): the shipped setup-gen/reward-gen agents are
    # VM-coupled (they drive env_cli.py against an Aliyun VM), so we do NOT load them.
    # `role` is for logging only; the self-contained prompt carries all instructions.
    # Auth: ANTHROPIC_API_KEY from .env (loaded into os.environ) → API mode.
    cmd = [
        "claude", "-p", prompt,
        "--permission-mode", "dontAsk",
        "--allowedTools", "Read,Write,Edit,Bash,Glob,Grep",
    ]
    return subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout,
        env=os.environ.copy(), stdin=subprocess.DEVNULL,
    )


def load_status() -> dict:
    return json.loads(STATUS_FILE.read_text()) if STATUS_FILE.exists() else {}


def save_status(s: dict) -> None:
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATUS_FILE.write_text(json.dumps(s, indent=2))


def export_final(spec: dict, adv_dir: Path) -> None:
    out = FINAL / spec["id"]
    out.mkdir(parents=True, exist_ok=True)
    for f in ("initial_setup.py", "golden_patch.py", "reward.py"):
        shutil.copy(adv_dir / f, out / f)
    config = {
        "id": spec["id"],
        "instruction": spec["instruction"],
        "app_type": "mock_websites",
        "config": [{"type": "execute", "command": ["python3", "initial_setup.py"]}],
        "evaluator": {"type": "python", "url": "reward.py"},
    }
    (out / "config.json").write_text(json.dumps(config, indent=2))


def process_task(spec: dict, mock_url: str, max_rounds: int) -> dict:
    app = spec["app"]
    adv_dir = ADV / spec["id"]
    sandbox_dir = SANDBOX / spec["id"]
    adv_dir.mkdir(parents=True, exist_ok=True)
    sandbox_dir.mkdir(parents=True, exist_ok=True)
    schema = REPO / SCHEMA_REL.format(app=app)
    skill = REPO / SKILL_REL
    base_url = base_url_for(app)

    common = dict(app=app, skill=skill, schema=schema, instruction=spec["instruction"],
                  context=spec["context"], base_url=base_url)
    review = ""

    for rnd in range(1, max_rounds + 1):
        setup_p = SETUP_PROMPT.format(task_dir=adv_dir, **common)
        reward_p = REWARD_PROMPT.format(task_dir=sandbox_dir, **common)
        if review:
            setup_p += REVIEW_SUFFIX.format(review=review)
            reward_p += REVIEW_SUFFIX.format(review=review)

        rs = run_agent("setup-gen", setup_p, adv_dir)
        rr = run_agent("reward-gen", reward_p, sandbox_dir)
        if (sandbox_dir / "reward.py").exists():
            shutil.copy(sandbox_dir / "reward.py", adv_dir / "reward.py")

        missing = [f for f in ("initial_setup.py", "golden_patch.py", "reward.py")
                   if not (adv_dir / f).exists()]
        if missing:
            review = f"Round {rnd}: agent did not produce {missing}. setup stderr: {rs.stderr[-300:]} reward stderr: {rr.stderr[-300:]}"
            continue

        verdict = verify_task(adv_dir, mock_url=mock_url, python=VENV_PY, verbose=False)
        (adv_dir / "REVIEW.md").write_text(
            f"# Round {rnd}\n\nreward(initial)={verdict.get('reward_initial')}  "
            f"reward(golden)={verdict.get('reward_golden')}\n"
            f"forbidden_warnings={verdict.get('forbidden_warnings')}\n\n"
            f"## Verdict: {'PASS' if verdict['pass'] else 'FAIL'}\n\n"
            + "\n".join(verdict.get("steps", []))
        )
        if verdict["pass"]:
            export_final(spec, adv_dir)
            return {"status": "completed", "rounds": rnd, **verdict}

        review = (f"Round {rnd} FAILED. reward(initial)={verdict.get('reward_initial')} "
                  f"(must be 0.0), reward(golden)={verdict.get('reward_golden')} (must be 1.0). "
                  f"warnings={verdict.get('forbidden_warnings')}. "
                  f"Diagnostics:\n" + "\n".join(verdict.get("steps", [])))

    return {"status": "failed", "rounds": max_rounds, "last_review": review}


def main():
    ap = argparse.ArgumentParser(description="Local web-only CUA-Gym pipeline (no VM)")
    ap.add_argument("specs", help="JSON file of task specs")
    ap.add_argument("--mock-url", default="http://localhost:5173")
    ap.add_argument("--app", default=None, help="override mock app for all tasks")
    ap.add_argument("--max-rounds", type=int, default=MAX_ROUNDS)
    ap.add_argument("--only", default=None, help="run a single task_id")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()
    load_dotenv()

    specs = load_specs(args.specs)
    if args.app:
        for s in specs:
            s["app"] = args.app
    if args.only:
        specs = [s for s in specs if s["id"] == args.only]
    if args.limit:
        specs = specs[: args.limit]

    status = load_status()
    print(f"Loaded {len(specs)} task(s). mock={args.mock_url}\n")
    for i, spec in enumerate(specs, 1):
        if status.get(spec["id"], {}).get("status") == "completed":
            print(f"[{i}/{len(specs)}] {spec['id']}: already completed, skipping")
            continue
        print(f"[{i}/{len(specs)}] {spec['id']}: running adversarial loop...")
        try:
            res = process_task(spec, args.mock_url, args.max_rounds)
        except subprocess.TimeoutExpired:
            res = {"status": "timeout"}
        except Exception as e:  # noqa: BLE001
            res = {"status": "error", "error": str(e)}
        status[spec["id"]] = res
        save_status(status)
        icon = {"completed": "✓", "failed": "✗", "timeout": "⏰", "error": "!"}.get(res["status"], "?")
        extra = f"(reward init={res.get('reward_initial')} gold={res.get('reward_golden')}, {res.get('rounds')} rounds)" if res["status"] == "completed" else res.get("error", res.get("status"))
        print(f"    {icon} {res['status']} {extra}\n")

    done = sum(1 for s in status.values() if s.get("status") == "completed")
    print(f"\nDone. {done}/{len(specs)} completed -> output/final/")


if __name__ == "__main__":
    main()
