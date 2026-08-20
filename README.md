# Art Manager Agent

NOOA (NVIDIA Object-Oriented Agents) specialist that owns **codycarlson.art**.

## What it does

- Daily command board (ruthless prioritization)
- Per-piece high-intent North Dakota buyer hunting
- Sales briefs + pricing recommendations
- Content plans
- Site research + improvement proposals (implemented only via PR)
- **Always uses Google Drive** for storage and printouts

## Google Drive

Folder: **Art Manager**
- `Printouts/` — every ≤3 days (or sooner if pressing)
- `Sales Briefs/`
- `Buyer Lists/`
- `State/`

First printout already live: [Printout 2026-08-20](https://docs.google.com/document/d/19of4TwIqB1YWwzBlUcjb3vyDrbCnyXocyExEi3ktWgg/edit)

Automation "Art Manager 3-Day Printout" is active.

## Current finished pieces

| ID              | Title           | Medium                    | Size   | Notes                          |
|-----------------|-----------------|---------------------------|--------|--------------------------------|
| `summer-walleye`| Summer Walleye  | Box elder wood carving    | 27"    | Outdoor UV + water protected   |
| `buffalo`       | Buffalo         | Acrylic on canvas         | 36×24  | Gaming-machine inspired        |

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
```

## Run

```bash
python -m agents.run_daily
```

## Safety model

All site changes are proposed as branch + pull request instructions.  
Nothing is pushed directly to `main` on codycarlson.art.

## Repo ownership

- Site: `hipaasynth-svg/codycarlson.art`
- Agent: this repo

## Next specialists (planned)

- AssetRecoveryAgent
- HipAAsynthAgent
- EatMinot / DrinkMinot agents
- TessomancyAgent
- GratefulSpacesAgent
- Orchestrator that manages Cody across all six
