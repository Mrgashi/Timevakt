#!/bin/bash
# Dry run: fetch the schedule and print notifications to stdout without touching
# the real state/snapshot.json (uses a separate state file in /tmp).
#
# Usage:
#   ./dryrun.sh              print-only (no pushes)
#   ./dryrun.sh --notify     send real pushes to the ntfy topic
#   ./dryrun.sh --simulate   tamper with the test snapshot first so change
#                            notifications fire even if nothing really changed
#   ./dryrun.sh --notify --simulate   full end-to-end test on your phone
set -e
cd "$(dirname "$0")"

STATE_FILE="/tmp/timeedit_test_snapshot.json"
TIMEEDIT_URL="https://cloud.timeedit.net/usn/web/publikk/ri1X5074f9506fQQ6YZYQQ8Y84y1Z106757.html"
NTFY_TOPIC=""
SIMULATE=0

for arg in "$@"; do
    case "$arg" in
        --notify)   NTFY_TOPIC="timeedit-usn-41ca806ea4f87b60" ;;
        --simulate) SIMULATE=1 ;;
        *) echo "unknown option: $arg" >&2; exit 2 ;;
    esac
done

if [ ! -d .venv ]; then
    python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

run_check() {
    STATE_FILE="$STATE_FILE" TIMEEDIT_URL="$TIMEEDIT_URL" NTFY_TOPIC="$NTFY_TOPIC" \
        .venv/bin/python check_schedule.py
}

if [ "$SIMULATE" = 1 ]; then
    # Make sure we have a baseline snapshot, then tamper with it so the next
    # check sees a time change, a room change, and a removed event.
    if [ ! -f "$STATE_FILE" ]; then
        echo "--- creating baseline snapshot first (no notifications expected) ---"
        NTFY_TOPIC="" run_check
    fi
    STATE_FILE="$STATE_FILE" .venv/bin/python - <<'EOF'
import json, os
from datetime import date, datetime

path = os.environ["STATE_FILE"]
state = json.load(open(path))
events = state["events"]
future = [eid for eid, ev in events.items()
          if datetime.strptime(ev["date"], "%d.%m.%Y").date() >= date.today()]
if len(future) < 3:
    raise SystemExit("not enough future events in the snapshot to simulate changes")

events[future[0]]["start"] = "07:00"           # -> "Time changed"
events[future[1]]["room"] = "Old room A-999"   # -> "Room changed"
events.pop(future[2])                          # reappears in fetch -> "New event"
events["FAKE-1"] = {                           # gone from fetch -> "REMOVED"
    "course": "TEST Fake course", "activity": "Forelesning",
    "date": (date.today().replace(year=date.today().year + 1)).strftime("%d.%m.%Y"),
    "start": "10:00", "end": "12:00", "room": "T-100", "teacher": "", "comment": "",
}
json.dump(state, open(path, "w"), indent=2, ensure_ascii=False, sort_keys=True)
print(f"Simulated: time change on {future[0]}, room change on {future[1]}, "
      f"new event {future[2]}, and one removed fake event")
EOF
    echo "--- running check against tampered snapshot ---"
fi

run_check
