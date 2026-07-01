# CUA-Gym Benchmark Report

- tasks: **6**  ·  models: **4**  ·  rollouts: **120**

## Task difficulty buckets

| Broken | Model-breaking | Too-easy | Productive |
|--:|--:|--:|--:|
| 1 | 1 | 1 | 3 |

## Model leaderboard

| Model | Pass rate | Mean reward | Fails | zero | partial | truncated | error | timeout | Mean steps |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| claude-opus | 57% | 0.62 | 13 | 0 | 4 | 7 | 2 | 0 | 5.1 |
| claude-sonnet | 43% | 0.52 | 17 | 0 | 5 | 9 | 3 | 0 | 5.0 |
| openai-cua | 33% | 0.39 | 20 | 0 | 4 | 11 | 4 | 1 | 4.9 |
| claude-haiku | 27% | 0.36 | 22 | 0 | 6 | 12 | 3 | 1 | 4.9 |

## Per-task buckets

| Task | Bucket | Oracle | Best pass-rate |
|---|---|---|--:|
| calc_003 | model_breaking | ok | 0% |
| docs_005 | broken | FAIL | 0% |
| gimp_002 | productive | ok | 60% |
| gmail_001 | too_easy | ok | 100% |
| gmail_007 | productive | ok | 100% |
| slack_009 | productive | ok | 80% |
