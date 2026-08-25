# Art Manager Agent

NOOA (NVIDIA Object-Oriented Agents) specialist that owns **codycarlson.art**.

## What it does

The agent's LLM-completed capabilities:

- Daily command board (ruthless prioritization)
- Per-piece high-intent North Dakota buyer hunting
- Sales briefs + pricing recommendations
- Content plans
- **Reads the live site** and diagnoses it as a selling tool (grounded in the
  real page, not a guess — see `agents/site.py`)
- Site improvement proposals (implemented only via PR)

## Hook it up (turning the portfolio into sales)

The site is a portfolio today. Four plug-in points turn it into something that
sells — each is independent, wire them in any order:

1. **Read the live gallery — already wired.** `agent.fetch_gallery()` fetches
 `https://codycarlson.art/api/gallery` and returns the real JSON catalog.
 `agent.fetch_site()` reads the **public page a buyer actually loads** and
 grounds it with that catalog: because the site is a client-rendered SPA, the
 gallery JSON is attached as `snapshot.gallery_data` (and merged into prices /
 images) so the diagnosis judges the real page, not the admin API.

2. **Mark what's for sale.** A piece becomes sellable when it has
   `for_sale=True`, a `price`, and a `buy_url`. Set these on the `ArtPiece`
   (and, on the website, add the same to `js/config.js` + a "Buy" button).
   `agent.get_sellable()` returns the pieces a buyer can pay for right now.

3. **Take payment → `buy_url`.** Easiest path with no backend: create a
   **Stripe Payment Link** (or Gumroad/Square link) per piece and paste it into
   that piece's `buy_url`. The agent then includes the pay link in briefs and
   outreach. (No global key needed — the link *is* the integration.)

4. **Find real buyers → `ART_MANAGER_SEARCH_API_KEY`.** Buyer hunting is only as
   real as its data source. Add a search API key (Google Places is best for
   local businesses — lodges, restaurants, designers, builders; Brave Search or
   SerpAPI also work) to turn AI-guessed buyer *types* into named, verifiable ND
   leads with links.

5. **Send the outreach → Gmail.** The agent drafts the emails; connect Gmail so
   it can send the ones you approve. (Authorize the Gmail connector in an
   interactive session — OAuth can't be done headless.)

## Status of integrations

The agent describes these behaviours in its prompts, but the surrounding
plumbing is at different stages. This table is the source of truth:

| Capability | Status | Notes |
|------------|--------|-------|
| LLM-completed methods (briefs, buyers, pricing, board) | ✅ Implemented | Filled in by nooa at runtime |
| Deterministic state helpers | ✅ Implemented | `agents/logic.py`, unit-tested |
| Local state persistence | ✅ Implemented | JSON on disk (`agents/state.py`) |
| Live gallery reading | ✅ Implemented | `agent.fetch_gallery()` returns `/api/gallery` JSON; `agent.fetch_site()` reads the public page and grounds it with that catalog |
| For-sale / checkout model | ✅ Implemented | `for_sale` + `buy_url` on `ArtPiece`; `get_sellable()` |
| Per-piece metadata / SEO | ✅ Implemented | `agents/seo.py`; `build_piece_seo()`, `export_seo_file()`; LLM enriches copy + AI-search research |
| Payments (checkout links) | 🔌 Bring your own | Per-piece Stripe/Gumroad link in `buy_url` (see **Hook it up**) |
| Real buyer search (named ND leads) | 🔌 Needs API key | `ART_MANAGER_SEARCH_API_KEY`; without it buyers stay AI-guessed |
| Send outreach email | 🔌 Needs Gmail | Agent drafts; connect Gmail to send |
| Google Drive persistence | 🚧 Planned | Folder IDs are configured; no Drive client is wired up yet |
| 3-day printout automation | 🚧 Planned | No scheduler exists in this repo yet |
| Site changes via GitHub PR | 🚧 Planned | The agent produces PR instructions; it does not open PRs itself |
| Content generation agent | ✅ Implemented | Separate `ContentAgent` (`agents/content_agent.py`) — TikTok/IG/FB captions, short scripts, visual briefs on a schedule; actual posting needs a connector |

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

## Inventory

Inventory comes entirely from the **live site** — `sync_from_gallery()` pulls
the real catalog from `/api/gallery` on every run. There are no hardcoded or
seeded pieces. (A piece that only exists locally, e.g. a carving not in the
paintings API, can still be added via `agent.add_piece(...)` and is preserved
across syncs.)

## Project layout

```
agents/
  models.py       # pydantic data models (framework-agnostic)
  logic.py        # pure deterministic helpers (no LLM / no nooa)
  seo.py          # deterministic per-piece meta tags + schema.org JSON-LD
  config.py       # env-driven configuration
  state.py        # local JSON state persistence
  content.py      # deterministic social scaffolding (hashtags, schedule, render)
  art_manager.py  # the nooa Agent subclass (LLM-completed methods)
  content_agent.py# separate nooa agent for TikTok/IG/FB content generation
  run_daily.py    # example runner
tests/            # unit tests for models / logic / config / state
```

`models`, `logic`, `config`, and `state` do not import nooa, so they can be
imported and tested without the agent runtime or an API key. Importing the
`agents` package is side-effect-free — the nooa agent and its LLM client are
built lazily the first time `ArtManagerAgent` is accessed.

## Quick start (Ubuntu / one command)

```bash
# 1. Paste your key in (prompts hidden; not saved to shell history):
read -rsp "Anthropic API key: " KEY && printf 'ANTHROPIC_API_KEY=%s\n' "$KEY" > .env && unset KEY; echo

# 2. Run everything:
./run.sh
```

`run.sh` creates a local `.venv`, installs dependencies on first run, and then
runs the daily workflow. Later runs reuse the venv and start immediately. It
needs **Python 3.12 or 3.13** on the machine (see below) and errors with an
install hint if it can't find one. Other modes: `./run.sh --tests` (test suite),
`./run.sh --setup` (install deps only).

## Setup (manual)

Requires **Python 3.12 or 3.13** (the [`nooa`](https://github.com/NVIDIA-NeMo/labs-OO-Agents)
runtime does not support 3.11 or 3.14+). On Ubuntu 22.04 or older, install it
with `sudo apt install python3.12 python3.12-venv`.

```bash
pip install -r requirements.txt
cp .env.example .env   # then open .env and paste your ANTHROPIC_API_KEY
```

The project-root `.env` is loaded automatically on startup, so no `export` is
needed — just keep your keys in `.env`. (Real environment variables still win
over `.env` if you set both.)

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
