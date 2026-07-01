# Local web-only pipeline (no VM, no Aliyun)

Run the CUA-Gym adversarial loop **entirely on your machine** for mock-website tasks
(Gmail by default), producing verified `(initial_setup, golden_patch, reward)` triples
you can export and benchmark in your own harness.

This bypasses the Aliyun/OSWorld VM substrate. It works because mock-website tasks are
pure HTTP against the mock's state API — the three scripts are plain `requests` calls,
so they run locally against a locally-hosted mock. **Web mocks only** (Gmail, Slack,
Notion, …) — desktop domains (calc, gimp, vs-code) still need the VM.

## How it maps to the real pipeline

| Real pipeline | Local harness |
|---|---|
| 2 isolated Aliyun VMs (`initial_env`, `golden_env`) | one local mock + two `sid`s |
| orchestrator drives `claude --agent` over `env_cli.py`/`:5000` | `run_local_pipeline.py` drives `claude -p`, scripts run as local subprocess |
| `reward(golden)==1.0 & reward(initial)==0.0` | identical check in `local_verify.py` |
| `reward_judge.py` (claude-sonnet via proxy) | `scripts/local/reward_judge.py` shim (gpt-4o, env-configurable) |
| `output/final/<id>/` | same — CUA-Gym-native output |

## One-time setup

```bash
# 1. mock app deps (once per mock)
cd hub/websites/gmail_mock && npm install && cd -

# 2. harness venv (requests + openai)
python3 -m venv .venv-local
.venv-local/bin/pip install -q requests openai

# 3. put your keys in .env (gitignored):
#      OPENAI_API_KEY=sk-proj-...      # reward.py LLM-judge tasks
#      ANTHROPIC_API_KEY=sk-ant-...    # claude -p generation
```

Requirements: Node/npm, Python 3.10+, and the `claude` CLI. The driver **loads `.env`
itself** (overriding the shell), so it uses your `.env` `ANTHROPIC_API_KEY` for headless
`claude` even if a stale/invalid key is exported in your shell profile. With no
`ANTHROPIC_API_KEY` set, `claude -p` falls back to your claude.ai login.

## Run it — ONE command (config-driven, recommended)

Edit `scripts/local/config.json` to pick types + counts (each app needs its own port):

```json
{
  "max_rounds": 5,
  "judge_model": "gpt-4o",
  "apps": [
    { "name": "gmail",           "count": 34, "port": 5173 },
    { "name": "google_calendar", "count": 33, "port": 5174 },
    { "name": "google_docs",     "count": 33, "port": 5175 }
  ]
}
```

Then:

```bash
.venv-local/bin/python scripts/local/generate.py
```

For each app this **auto-hosts the mock** (npm install on first run), **generates `count`
specs** via `claude -p` (schema-grounded → `output/task_generation/<app>.json`), runs the
**adversarial loop**, and **exports** verified tasks to `output/final/<id>/`. Resumable via
`output/local_batch_status.json`.

CLI overrides (no config edit needed):
```bash
.venv-local/bin/python scripts/local/generate.py --app gmail --count 100
.venv-local/bin/python scripts/local/generate.py --app google_calendar --count 30 --regen
.venv-local/bin/python scripts/local/generate.py --count 1            # smoke-test every app
```

`name` must match both `hub/websites/<name>_mock` and
`.claude/skills/mock_websites/schemas/<name>_mock.md`. Available types include gmail,
google_calendar, google_docs, slack, github, notion, asana, jira, trello, … (run
`ls .claude/skills/mock_websites/schemas/` to see all).

Verified tasks land in `output/final/<id>/` as `{config.json, initial_setup.py,
golden_patch.py, reward.py}`.

### Manual flow (if you already have a specs JSON)

```bash
scripts/local/start_mock.sh gmail 5173        # host one mock
.venv-local/bin/python scripts/local/run_local_pipeline.py \
    output/task_generation/gmail.json --mock-url http://localhost:5173 --app gmail
```

## Benchmark in your own pipeline

Per task: start the mock, then
1. run `initial_setup.py` (builds the starting inbox at a fresh `sid` in `/tmp/task_web_sid`)
2. let **your model** act against `http://localhost:5173/?sid=<sid>`
3. run `reward.py` → reads the last `REWARD: X.X` line = your model's score (0.0–1.0)

`config.json.evaluator.url` points at `reward.py`; `config[].command` runs the setup.

## Knobs

- `generate.py --app <name> --count N --port P --regen --only id1,id2 --max-rounds N`
- `CUA_GYM_JUDGE_MODEL=gpt-4o-mini` cheaper judge · set `OPENAI_BASE_URL` to use a proxy model
- verify a hand-made triple directly:
  `.venv-local/bin/python scripts/local/local_verify.py <task_dir> --mock-url http://localhost:5173`

## Multi-word mocks (google_calendar, google_docs, aws_console, …)

The public host uses **hyphens**, not underscores: `google_calendar` → `cua-gym-google-calendar.xlang.ai`.
The generator emits the hyphenated host and the localizer matches both hyphen and underscore
variants, so this is handled automatically — just put the underscore name (the mock dir name)
in `config.json`.

## Troubleshooting

- **A web-mock reward fails `0.0 / 0.0` (both envs):** usually the script's `BASE_URL` host
  couldn't be reached/localized — confirm it's a `cua-gym-*.xlang.ai` URL (the localizer only
  rewrites those) using hyphens. The loop normally self-corrects within a few rounds.
- **`claude -p` "Invalid API key":** a stale `ANTHROPIC_API_KEY` in your shell. The driver
  loads `.env` (override) to fix this; make sure your valid key is in `.env`.
- **Mock won't start / port busy:** pick a different `port` in `config.json`, or check
  `curl -s localhost:<port>/go?sid=probe`.
- **Resume after a stop:** just rerun the same command — completed tasks (in
  `output/local_batch_status.json`) are skipped.

## Files

| File | Role |
|---|---|
| `generate.py` | **main entry** — config-driven: per app auto-host mock → gen specs → loop → export |
| `config.json` | choose types + counts + ports + judge model |
| `run_local_pipeline.py` | per-spec driver: `claude -p` gen (info-barrier) → verify → retry → export |
| `local_verify.py` | dual-env PASS check (localizes URLs + neutralizes Chrome, runs the 3 scripts) |
| `reward_judge.py` | env-configurable LLM-judge shim (drop-in for `utils/reward_judge.py`) |
| `start_mock.sh` | launch one mock locally (Vite serves UI + state API) |
