# CLAUDE.md

Project context for Claude Code (and humans) working in **CUA-Gym**. This file loads automatically each session.

## What this repo is

CUA-Gym is a **scalable pipeline that synthesizes verifiable RLVR training data for computer-use agents (CUAs)**. The unit of value is a verified **triple**: `(task instruction, executable environment state, verifiable reward function)`. Hand-authoring one takes hours; CUA-Gym automates it with coding agents.

- Paper: arXiv 2605.25624 · Org: `xlang-ai` · Dataset: HF `xlangai/CUA-Gym` (**32,112** verified tuples)
- Coverage: **110 environments** = 16 desktop apps + 94 mock web apps
- License: code Apache-2.0, dataset CC BY 4.0
- Built on the **OSWorld** evaluation substrate (`OSWORLD_DIR=~/OSWorld-RL`, venv `~/.venvs/osworld-py312`)

## Pipeline (end to end)

```
USER PROMPT
  → task-gen ............... output/task_generation/<topic>.json   (plan-mode: research→taxonomy→matrix→3-pass)
  → batch_orchestrator.py .. spawns `claude --agent orchestrator` per task (async, concurrency-limited, resumable)
  → ADVERSARIAL LOOP ....... ≤5 rounds on TWO isolated VMs (initial_env, golden_env)
  → majority-vote filter ... filter/ LLM critic: keep / modify_query / reject
  → output/final/<task_id>/  {config.json, initial_setup.py, golden_patch.py, reward.py, REVIEW.md}
```

### The adversarial loop (the core idea)
- **orchestrator** (`.claude/agents/orchestrator.md`) — drives the loop, generates NO code. Creates 2 VMs, spawns the two agents, reads `REVIEW.md`, collects `output/final/`, deletes VMs.
- **setup-gen** = Generator (`setup-gen.md`) — writes `initial_setup.py` (pre-task state) on `initial_env` and `golden_patch.py` (correct post-task state) on `golden_env`.
- **reward-gen** = Discriminator (`reward-gen.md`) — writes `reward.py` (progressive 0.0–1.0, prints `REWARD: X.X`). Works in an **information-barrier sandbox**: it cannot see setup-gen's code and must verify from the task description alone.
- **PASS** when all 5 hold: setup runs ✓ · patch runs ✓ · `reward(golden)==1.0` ✓ · `reward(initial)==0.0` ✓ · no forbidden patterns ✓.

## Repo layout

| Path | What |
|------|------|
| `.claude/agents/*.md` | The 4 pipeline agents (prompts, not Python): task-gen, orchestrator, setup-gen, reward-gen |
| `.claude/skills/<domain>/SKILL.md` | Domain knowledge loaded by setup/reward-gen: how to create (§1) & verify (§2) each domain + bitter lessons (§3) |
| `.claude/skills/mock_websites/` | Web-layer skill + `schemas/<mock>.md` (state specs) |
| `.claude/commands/create-skill.md` | `/create-skill <domain>` — authors a SKILL.md by mining OSWorld evaluator source |
| `scripts/batch_orchestrator.py` | Async driver; one orchestrator run per task; resumable via `output/batch_status.json` |
| `scripts/env_cli.py` | CLI over `utils.env.Env`; how agents drive the VM (run-python, upload, screenshot, …) |
| `scripts/materialize_dataset_urls.py` | Swaps `__CUA_GYM_*_URL__` placeholders in released dataset bundles |
| `scripts/local/` | **Local web-only pipeline (no VM/Aliyun)** for mock-website tasks; see `scripts/local/README.md` |
| `scripts/benchmark/` | **Model-benchmarking harness** — runs Claude/OpenAI computer-use models against `output/final/` tasks and classifies each (Broken/Model-breaking/Too-easy/Productive) via an oracle control + per-model pass-rates. Web tasks run REAL GUI rollouts locally via Playwright/Chromium (`web_backend.py`, no Aliyun); desktop tasks use the VM (`env_backend.VMBackend`). Reports: `index.html` (Overview + Deep Dive trajectory viewer), `report.html`, `report_detail.html`. See `scripts/benchmark/README.md` |
| `utils/env.py` | VM lifecycle (Aliyun ECS); talks HTTP to an agent on the VM at `:5000` |
| `utils/llm_utils.py` | Cached, provider-agnostic LLM layer (OpenAI + Claude) |
| `utils/reward_judge.py` | **Locked-down** LLM/vision judge deployed to the VM (`/tmp/reward_judge.py`) so rewards can't cheat |
| `utils/logger.py` | Thread-safe pipeline logger (contextvars: task/module/stage) |
| `filter/` | `majority_vote_filter.py` (N-vote critic), `critic_prompt.py`, `run_critic_benchmark.py`, `taxonomy.yaml`, `benchmark_tasks.json` |
| `hub/` | git submodule → CUA-Gym-Hub (the 94 mock web apps). **Empty until `git submodule update --init`** |

## The web environment layer (CUA-Gym-Hub)

94 of 110 envs are mock web apps. Two design choices make each a reusable RL env:
1. **State injection** — a task ships its own JSON initial state + `reward.py`, so one mock hosts unlimited task-worlds with no code change.
2. **Session isolation** — every URL carries `?sid=<id>`, so parallel RL workers on the same mock never collide.

Unified HTTP state API (every mock): `POST /post?sid=` (`set` = current+initial, `set_current` = current only, `reset`), `GET /go?sid=` → `{initial_state, current_state, state_diff}`, `GET /state?sid=`, `POST /upload?sid=`. The `sid` flows via `/tmp/task_web_sid` across `initial_setup.py` → `golden_patch.py` → `reward.py`. The state API is a **Vite middleware in each mock's `vite.config.js`** (both dev + preview), so `npm run dev` alone serves it — state persists to `<mock>/.mock-states/<sid>.json`.

### Local web-only pipeline (`scripts/local/`) — run the loop with NO VM
For mock-website tasks only, the whole adversarial loop runs locally (no Aliyun/OSWorld). Entry point: `scripts/local/generate.py` — config-driven (`config.json`: `apps=[{name,count,port}]`, `max_rounds`, `judge_model`), per app it auto-hosts the mock (`npm run dev`), generates `count` specs via `claude -p` → `output/task_generation/<app>.json`, runs the loop, exports `output/final/<id>/` (CUA-Gym-native). Under the hood `run_local_pipeline.py` drives `claude -p` (NOT the VM-coupled `--agent` prompts) to write the 3 scripts under an info-barrier (setup→`output/adversarial/`, reward→`output/reward_sandbox/`), and `local_verify.py` runs them as local subprocesses against the mock with two `sid`s (the two envs), checking `reward(initial)==0 & reward(golden)==1`. It localizes scripts at run time (`cua-gym-*.xlang.ai`→local URL, `google-chrome`→`true`) and uses `scripts/local/reward_judge.py` (default gpt-4o, env `CUA_GYM_JUDGE_MODEL`) instead of the locked-down judge. Auth: the driver **loads `.env`** (overriding the shell) so headless `claude` uses the `.env` `ANTHROPIC_API_KEY`; `OPENAI_API_KEY` powers the judge. Needs `.venv-local` (requests+openai) + the `claude` CLI. An app is usable if it has BOTH `hub/websites/<app>_mock` and `schemas/<app>_mock.md` (gmail, google_calendar, google_docs, slack, github, notion, … ✓). Desktop domains still require the VM. See `scripts/local/README.md`.

## CONVENTIONS & INVARIANTS (break one → tasks silently fail verification)

- **Dual-env, not filename suffixes.** State separation is by VM (`initial_env` vs `golden_env`). `golden_patch.py` builds golden state from scratch in `golden_env` — NEVER copy a file from `initial_env`.
- **Information barrier.** reward-gen lives in `output/reward_sandbox/<task_id>/` with only task_config + env_configs. It must NOT read setup-gen scripts and must NOT download artifacts locally — explore the VM via `env_cli.py` only.
- **Path rule.** Orchestrator files go under `output/adversarial/<id>/`, `output/reward_sandbox/<id>/`, or `output/final/<id>/`. Bare `output/<id>/` is a bug.
- **Scripts run ON the VM.** `initial_setup`/`golden_patch`/`reward` all use `WORKDIR='/home/user'` and run via `env_cli.py run-python`. Never run them locally. GUI launches need `DISPLAY=:0` + non-blocking `subprocess.Popen`.
- **reward.py:** progressive float, `REWARD: X.X` last line, scores ONLY task-introduced changes (FAIL on initial → 0.0, PASS on golden → 1.0). Forbidden: hardcoded `True`/`return 1.0`, subprocess, file-existence scoring, raw `from openai import OpenAI`. LLM judge ≤40% of score (≤50% vision), only via `from reward_judge import call_llm_judge`, each call needs a `# JUSTIFICATION:` comment.
- **mock_websites:** `golden_patch.py` MUST use `action:"set_current"` (NEVER `"set"` — it overwrites initial_state, empties state_diff, breaks the reward). Inject ALL required schema top-level keys (missing → blank page). Inject state BEFORE launching Chrome. Same sid across multi-mock tasks.
- **Final `config.json` field names:** `instruction`/`id`/`app_type`/`config`/`evaluator` (NOT task_instruction/task_id). `config` = download+execute (run setup with `python3`); `evaluator` = `{type: python, url}`.
- **Multimedia tasks** (gimp/vlc/openshot): `initial_setup.py` must save `<task_id>_initial_reference.<ext>` (untouched) for the vision judge's BEFORE image.
- **Agreement = trust REVIEW.md.** Orchestrator decides PASS solely from the line `## Verdict: PASS`; it does not re-verify.

## Gotchas / things that aren't obvious

- **65 mock schema files on disk, only 16 mocks deployed.** Live registry (in `mock_websites/SKILL.md`): asana, aws_console, discord, docusign, github, gitlab, gmail, jira, linkedin, notion, reddit, salesforce, slack, trello, twitter, youtube. The other 49 are spec'd-but-not-deployed — **task generation should target only the 16 live mocks.**
- `hub/` submodule is **empty locally** until initialized; `output/` does not exist until the pipeline runs.
- `.claude/commands/create-skill.md` references the author's hardcoded path `/Users/bowen/.../OSWorld/` — won't exist on other machines.
- Permissions are wide open in `.claude/settings.json` (`Bash/Write/Edit/Read/Glob/Grep(*)`).

## Setup / commands

```bash
pip install -e ".[dev]"          # Python ≥3.10
cp .env.example .env             # fill OPENAI_API_KEY + ALIYUN_* (VM provider) + OSWORLD_DIR/VENV
git submodule update --init      # only if working on the mock web apps (hub/)

ruff check . && ruff format .    # lint/format (line-length 100, py310, rules E/F/I)

# Run the pipeline for a domain
python scripts/batch_orchestrator.py output/task_generation/<topic>.json
# Filter verified tasks
python filter/majority_vote_filter.py --tasks-dir output/final --votes 3 --model gpt-4o --write
# Benchmark a critic model (run after filter changes; report before/after)
python filter/run_critic_benchmark.py --model <model>
```

## Required env vars (`.env`)
`OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`, `ANTHROPIC_API_KEY`) · `ALIYUN_*` (ECS VM provider) · `OSWORLD_DIR`, `OSWORLD_VENV` · optional `SSH_GATEWAY_*` (legacy remote orchestration).

## Domain skill quick map
Desktop/file: libreoffice-calc (openpyxl), libreoffice-writer (python-docx), libreoffice-impress (python-pptx), pdf (PyMuPDF/pikepdf/reportlab), gimp (Pillow/numpy/SSIM), os (os/shutil/gsettings), vs-code (json settings, merge-don't-overwrite), chrome (sqlite3+CDP; FILETIME timestamps), vlc (vlcrc+HTTP), blender (bpy headless), openshot (.osp JSON), drawio/excalidraw (Playwright/localStorage), grafana/overleaf/penpot (HTTP, per-session isolation). Each `SKILL.md` has the authoritative API + bitter lessons — read it before generating setup/reward code for that domain.
```
