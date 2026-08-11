# TimeEdit schedule warnings

**What is this?** USN publishes our teaching schedule on TimeEdit, but when a lecture is moved, cancelled, or changes room, nothing tells you — you only find out by re-checking the page (or by showing up to an empty classroom). This project fixes that: it watches the TimeEdit schedule for **Informasjonssystemer, Campus Hønefoss** around the clock and sends a push notification to your phone within minutes-to-an-hour of any change.

You get warned about:
- ⏰ **Time changes** (high priority)
- ❌ **Cancelled or removed sessions** (max priority — breaks through silent mode)
- 🚪 **Room changes** and 🗓️ **new sessions** (normal priority)

It runs entirely on GitHub's servers — nobody's computer needs to be on, and there is nothing to install except the notification app on your phone.

## How to get notified

1. Install the free **ntfy** app ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy) / [iPhone](https://apps.apple.com/us/app/ntfy/id1625396347)).
2. In the app, tap **Add subscription** and enter the topic name — ask the repo owner for it (it's a secret: the name is the only thing protecting the channel, so it's not written down here and shouldn't be shared publicly).
3. Done. You'll now get the same notifications as everyone else subscribed to the topic. No account needed.

## How it works

`check_schedule.py` fetches the schedule's `.json` export, compares it to the last snapshot in `state/snapshot.json`, sends one [ntfy](https://ntfy.sh) push per change, and saves the new snapshot. GitHub Actions ([.github/workflows/check.yml](.github/workflows/check.yml)) runs it on a cron schedule and commits the snapshot back, so no external database is needed. See [PLAN.md](PLAN.md) for the full design.

Check cadence (Norwegian local time, cron is defined in UTC):
- every 5 min from 06:00 to 07:30 Oslo time, DST-safe (morning burst — warns before you travel)
- hourly during the day
- evening checks between ~21:00 and midnight (catches changes posted the night before)

The first run just saves a baseline and stays silent. If fetching fails twice in a row, you get a "checker is broken" push so silence never accidentally means "all clear". You also get a warning when the published schedule window is about to run out.

## Maintainer setup

The push target lives in the `NTFY_TOPIC` repo secret (Settings → Secrets and variables → Actions). It can hold several comma-separated topics; every notification is pushed to each of them — useful for giving each person their own topic so one can be removed later. Trigger a manual check anytime from the Actions tab → "Check TimeEdit schedule" → Run workflow.

## Running locally

```sh
./dryrun.sh                       # fetch + print what would be notified, no pushes
./dryrun.sh --notify --simulate   # fake some changes and push real test notifications
```

Or run the checker directly:

```sh
pip install -r requirements.txt
TIMEEDIT_URL="https://cloud.timeedit.net/usn/web/publikk/ri1X5074f9506fQQ6YZYQQ8Y84y1Z106757.html" \
NTFY_TOPIC="<your-topic>" python check_schedule.py
```

Leave `NTFY_TOPIC` unset to print notifications to stdout without pushing.

## Changing the schedule being watched

Edit `TIMEEDIT_URL` in `.github/workflows/check.yml` (and `dryrun.sh`), delete `state/snapshot.json`, and commit — the next run rebuilds the baseline silently.
