# Art Manager Agent

NOOA (NVIDIA Object-Oriented Agents) specialist that owns **codycarlson.art**.

## What it does

- Daily command board (ruthless prioritization)
- Per-piece high-intent North Dakota buyer hunting
- Sales briefs + pricing recommendations
- Content plans
- Site research + improvement proposals (implemented only via PR)
- **Always** persists to Google Drive
- Printouts every ≤ 3 days (Automation active)

## Live Google Drive

[Art Manager folder](https://drive.google.com/drive/folders/1uzI3VXasnvl-4_KemHN60dgwBP1_q4vr)

| Folder | ID |
|--------|----|
| Root | `1uzI3VXasnvl-4_KemHN60dgwBP1_q4vr` |
| Printouts | `1WUh8YNYO7736eUwhU0EctoM9wZWOHARM` |
| Sales Briefs | `1s3nujmMevAOGWvfCk-dwZf5l0SVuS2HB` |
| Buyer Lists | `103wQVeWOo-gVdeglZD_w7jwNbGsdnXJZ` |
| State | `1shpW9nOsr6EOHNblz23NUiZWIUucrlV4` |

## Current finished pieces

| ID | Title | Medium | Size | Notes |
|----|-------|--------|------|-------|
| `summer-walleye` | Summer Walleye | Box elder wood carving | 27" | Outdoor UV + water protected |
| `buffalo` | Buffalo | Acrylic on canvas | 36×24 | Gaming-machine inspired |

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

## Automation

`Art Manager 3-Day Printout` is active and writes to the Printouts folder.
