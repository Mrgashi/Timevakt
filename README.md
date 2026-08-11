# TimeEdit schedule warnings

Watches a TimeEdit schedule (USN, Campus Hønefoss) and pushes a phone notification via [ntfy](https://ntfy.sh) when a teaching session's **time changes**, it is **cancelled/removed**, or (informationally) a **room changes** or a **new event** appears. See [PLAN.md](PLAN.md) for the full design.

## How it works

`check_schedule.py` fetches the schedule's `.json` export, compares it to the last snapshot in `state/snapshot.json`, sends one ntfy push per change, and saves the new snapshot. GitHub Actions ([.github/workflows/check.yml](.github/workflows/check.yml)) runs it on a cron schedule and commits the snapshot back, so no external database is needed.

Check cadence (Norwegian local time, cron is defined in UTC):
- every 5 min from 06:00 to 07:30 Oslo time, DST-safe (morning burst — warns before you travel)
- hourly during the day
- one evening check around 21:00

The first run just saves a baseline and stays silent. If fetching fails twice in a row, you get a "checker is broken" push so silence never accidentally means "all clear".

## Setup

1. Install the **ntfy** app on your phone and subscribe to the secret topic (stored as the `NTFY_TOPIC` repo secret on GitHub — Settings → Secrets and variables → Actions). `NTFY_TOPIC` can hold several comma-separated topics; every notification is pushed to each of them.
2. That's it. Trigger a manual check anytime from the Actions tab → "Check TimeEdit schedule" → Run workflow.

## Running locally

```sh
pip install -r requirements.txt
TIMEEDIT_URL="https://cloud.timeedit.net/usn/web/publikk/ri1X5074f9506fQQ6YZYQQ8Y84y1Z106757.html" \
NTFY_TOPIC="<your-topic>" python check_schedule.py
```

Leave `NTFY_TOPIC` unset to print notifications to stdout without pushing.

## Changing the schedule being watched

Edit `TIMEEDIT_URL` in `.github/workflows/check.yml`, delete `state/snapshot.json`, and commit — the next run rebuilds the baseline silently.
