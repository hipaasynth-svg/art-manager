# Studio Operating Manual (SOP)

How the daily packet gets turned into sales, and how the studio stays in sync.
Two roles: **the caller** (Cody or a hired helper) works the leads; **Cody**
approves and keeps inventory honest.

## What arrives each morning
One email ("Art Manager — daily brief") with, in order:

1. **Command board** — the 1 thing to do today + what to ignore.
2. **Call sheet** — real ND businesses, phone numbers, why each fits, and a
   read-aloud script per lead.
3. **Sales brief** — paste-ready copy for the day's top piece.
4. **Content pack** — an Instagram caption + a TikTok script for that piece.

## The caller's loop (≈45–60 min/day)
1. Work the **Call Sheet** top to bottom. Read the script, but sound human.
2. Log every call with one word: **interested / not now / no**. Add the email or
   a callback time when you get one. (Keep this in the shared tracker — a Google
   Sheet or Zoho Projects board; ask Cody which.)
3. For "interested": send the piece photo + the `?buy=` link the same day, or
   set the drop-off time. Consignment pitch = "one piece, two-week trial."
4. For gift shops / cafés / clinics: the ask is a **local-artist wall** or
   **lobby placement** + "commission your pet/place" cards, not a hard sale.
5. Never argue or push. One good call beats ten. Move on.

## Posting content (whoever runs social)
- Use the **Content Pack**. Shoot the visual it describes on a phone.
- Post to Instagram + Facebook; use the TikTok script for a 20–40s reel.
- Always include the buy link when the piece is for sale. Keep the studio voice
  (see `STYLE_BIBLE.md`) — plain, maker-first, no hype.

## Cody's upkeep (5 min, keeps the whole thing honest)
State drift is the enemy — if a piece moves and the site doesn't know, every
downstream draft is wrong. So:

1. **When a piece sells or leaves the studio:** mark it **Sold/Reserved** in
   `/admin` on codycarlson.art that day. (On-site purchases auto-mark via the
   Stripe webhook; consignment/drop-offs you mark by hand.)
2. **Approve outreach:** nothing goes to a buyer without your yes. The agent
   drafts; you (or the caller) send.
3. **Deposit before work:** no commission starts without the deposit.
4. **Fix the voice once:** if a draft sounds off, edit `STYLE_BIBLE.md` — don't
   re-explain it every time. The next run picks it up.
5. **Glance at the command board's "IGNORE" line.** It's protecting your time on
   purpose.

## When to grow the system
Add the heavier machinery (a real CRM cadence, COA packets for the $500+
sculptures, a task board for the caller) once pieces are moving weekly and a
couple of commissions are in flight — not before. Until then, the job is
**calls, content, and closing the first few sales.**

## Knobs
- Pieces worked per day: `ART_MANAGER_DAILY_PIECES` (default 4; the run rotates
  through the whole catalog over several days).
- Studio voice: `STYLE_BIBLE.md` (edit freely; takes effect next run).
