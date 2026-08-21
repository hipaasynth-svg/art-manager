# Art Manager Agent

NOOA (NVIDIA Object-Oriented Agents) specialist that owns **codycarlson.art**.

## What it does

The agent's LLM-completed capabilities:

- Daily command board (ruthless prioritization)
- Per-piece high-intent North Dakota buyer hunting
- Sales briefs + pricing recommendations
- Content plans
- Site research + improvement proposals (implemented only via PR)

## Status of integrations

The agent describes these behaviours in its prompts, but the surrounding
plumbing is at different stages. This table is the source of truth:

| Capability | Status | Notes |
|------------|--------|-------|
| LLM-completed methods (briefs, buyers, pricing, board) | ✅ Implemented | Filled in by nooa at runtime |
| Deterministic state helpers | ✅ Implemented | `agents/logic.py`, unit-tested |
| Local state persistence | ✅ Implemented | JSON on disk (`agents/state.py`) |
| Google Drive persistence | 🚧 Planned | Folder IDs are configured; no Drive client is wired up yet |
| 3-day printout automation | 🚧 Planned | No scheduler exists in this repo yet |
| Site changes via GitHub PR | 🚧 Planned | The agent produces PR instructions; it does not open PRs itself |

State currently persists to a local JSON file (see **State** below). Drive as
the long-term home is a follow-up.

## Live Google Drive

[Art Manager folder](https://drive.google.com/drive/folders/1uzI3VXasnvl-4_KemHN60dgwBP1_q4vr)

| Folder | ID |
|--------|----|
| Root | `1uzI3VXasnvl-4_KemHN60dgwBP1_q4vr` |
| Printouts | `1WUh8YNYO7736eUwhU0EctoM9wZWOHARM` |
| Sales Briefs | `1s3nujmMevAOGWvfCk-dwZf5l0SVuS2HB` |
| Buyer Lists | `103wQVeWOo-gVdeglZD_w7jwNbGsdnXJZ` |
| State | `1shpW9nOsr6EOHNblz23NUiZWIUucrlV4` |

These IDs are the defaults; override them via `ART_MANAGER_DRIVE_*` env vars.

## Current finished pieces

| ID | Title | Medium | Size | Notes |
|----|-------|--------|------|-------|
| `summer-walleye` | Summer Walleye | Box elder wood carving | 27" | Outdoor UV + water protected |
| `buffalo` | Buffalo | Acrylic on canvas | 36×24 | Gaming-machine inspired |

## Project layout

```
agents/
  models.py       # pydantic data models (framework-agnostic)
  logic.py        # pure deterministic helpers (no LLM / no nooa)
  config.py       # env-driven configuration
  state.py        # local JSON state persistence
  art_manager.py  # the nooa Agent subclass (LLM-completed methods)
  run_daily.py    # example runner
tests/            # unit tests for models / logic / config / state
```

`models`, `logic`, `config`, and `state` do not import nooa, so they can be
imported and tested without the agent runtime or an API key. Importing the
`agents` package is side-effect-free — the nooa agent and its LLM client are
built lazily the first time `ArtManagerAgent` is accessed.

## Setup

Requires **Python 3.12 or 3.13** (the [`nooa`](https://github.com/NVIDIA-NeMo/labs-OO-Agents)
runtime does not support 3.11 or 3.14+).

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY=your_key_here
```

## Configuration

All configuration is via `ART_MANAGER_*` environment variables with sensible
defaults (see `.env.example` and `agents/config.py`). Nothing is required
except `ANTHROPIC_API_KEY` to actually call the model.

## Run

```bash
python -m agents.run_daily
```

## State

State (pieces, pipeline, revenue, focus) persists to a local JSON file so it
survives between runs. Default path `art_manager_state.json` (gitignored);
override with `ART_MANAGER_STATE_PATH`.

## Tests

The framework-agnostic tests (models/logic/config/state) need only pydantic +
pytest and run on any interpreter. On Python 3.12/3.13 the additional nooa
regression tests run too; elsewhere they skip automatically.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

CI runs the suite on Python 3.12 and 3.13 on every push and pull request
(`.github/workflows/ci.yml`).

## Safety model

All site changes are proposed as branch + pull request instructions.
Nothing is pushed directly to `main` on codycarlson.art.
