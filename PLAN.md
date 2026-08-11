# TimeEdit Schedule Change Warning System

## Context

You travel to teaching sessions and want an early warning if a session's time changes or gets cancelled, so you don't travel for nothing. The schedule is a public TimeEdit view at USN (Campus Hønefoss):
`https://cloud.timeedit.net/usn/web/publikk/ri1X5074f9506fQQ6YZYQQ8Y84y1Z106757.html`

**Verified:** swapping `.html` → `.json` returns clean structured data — `reservations` with `id`, `startdate` (DD.MM.YYYY), `starttime`, `enddate`, `endtime`, and `columns` = [studentgruppe, emne, aktivitet, rom, –, kommentar, ansatt]. No login needed.

The checker must run in the cloud (works even when your Mac is asleep / you've left home), scan frequently in the morning up until about an hour before class start, and push a warning to your phone via the free **ntfy** app.

## Architecture

- **Runner:** GitHub Actions on a cron schedule (free for a private repo at this usage level).
- **Data source:** the verified `.json` export of your TimeEdit view (URL above with `.json` extension).
- **Change detection:** Each run fetches the schedule and compares it to the previous snapshot committed in the repo (`state/snapshot.json`). After each run the workflow commits the new snapshot back, so state survives between runs with no external database.
- **Notification:** On any relevant change, POST a message to `https://ntfy.sh/<secret-topic>`. You subscribe to that topic in the ntfy phone app (and optionally the ntfy desktop app on the Mac for a popup there too).

## What counts as a warning

For each event (matched by TimeEdit's reservation `id`, falling back to course+date):
- **Time changed** — start or end time (or date) differs from the snapshot → high-priority push: "⚠️ Webutvikling og HCI moved: Wed 10:00–14:00 → Wed 12:00–16:00".
- **Cancelled** — event disappeared from the schedule, or activity/comment contains a cancellation marker ("avlyst"/"utgår"/"cancelled") → max-priority push.
- **New event added** and **room changed** — normal-priority push (informational).
- No change → no notification (silent).

## Files to create

```
timeedit_warnings/
├── check_schedule.py          # fetch → parse → diff vs snapshot → notify → write snapshot
├── state/snapshot.json        # last-seen schedule (committed by the workflow)
├── .github/workflows/check.yml
├── requirements.txt           # requests
└── README.md                  # setup notes
```

### check_schedule.py
Python 3, config via env vars `TIMEEDIT_URL` (the public link — not secret) and `NTFY_TOPIC` (GitHub secret). Steps: fetch the `.json` export, normalize reservations to `{id, course, activity, date, start, end, room, teacher, comment}` (course from column "Emne", activity from "Aktivitet", etc.), load `state/snapshot.json`, compute diffs per the rules above, send one ntfy message per change (title, priority, tags), write new snapshot. Exit non-zero on fetch/parse failure so a broken link is visible in the Actions log — and after 2 consecutive fetch failures (tracked in the snapshot file), send a "checker is broken" push so silence never accidentally means "all clear".

### .github/workflows/check.yml
Cron entries (note: GitHub cron is **UTC**; Norway is UTC+1/+2, and Actions crons can fire several minutes late — the morning schedule is chosen with margin):
- **Morning burst:** every 15 min from 06:00–09:00 local time (your current schedule's teaching mostly starts at 10:00, so this covers "scan often until ~1 h before start" with margin for earlier starts).
- **Baseline:** hourly 08:00–18:00 local, plus one evening check ~21:00 (catches changes posted the night before).

Job: checkout → run script → `git commit` + push `state/snapshot.json` if changed. Also `workflow_dispatch:` so you can trigger a check manually from the phone/browser.

## Setup steps (part of implementation)

1. Initialize git repo, create a **private** GitHub repo, push (needs `gh auth` or your GitHub login).
2. Add repo secret `NTFY_TOPIC` — a long random topic name (the topic name is the only "password" on ntfy.sh).
3. You install the **ntfy** app on your phone and subscribe to that topic (I'll give you the exact name).

## Verification

1. Run `TIMEEDIT_URL=... NTFY_TOPIC=... python check_schedule.py` locally — confirm it fetches, parses, and writes a sane snapshot.
2. Manually edit a time in `state/snapshot.json`, rerun — confirm a "time changed" push arrives on the phone.
3. Delete an event from the snapshot, rerun — confirm a "new event" push; do the reverse for "cancelled".
4. Push to GitHub, trigger the workflow via `workflow_dispatch`, confirm the run passes and commits the snapshot.
