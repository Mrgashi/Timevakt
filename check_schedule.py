#!/usr/bin/env python3
"""Check a TimeEdit schedule for changes and push warnings via ntfy.

Env vars:
  TIMEEDIT_URL  - TimeEdit schedule view URL (.html or .json)
  NTFY_TOPIC    - ntfy.sh topic to push notifications to
  STATE_FILE    - path to snapshot file (default: state/snapshot.json)
"""

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

import requests

TIMEEDIT_URL = os.environ["TIMEEDIT_URL"]
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
STATE_FILE = Path(os.environ.get("STATE_FILE", "state/snapshot.json"))

CANCEL_MARKERS = ("avlyst", "utgår", "utgaar", "cancelled", "canceled", "innstilt", "inställd")

# columnheaders: ["Studentgruppe", "Emne, Emne", "Aktivitet", "Rom", "", "Egen tekst, Kommentar", "Ansatt"]
COL_COURSE, COL_ACTIVITY, COL_ROOM, COL_COMMENT, COL_TEACHER = 1, 2, 3, 5, 6

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def notify(title: str, message: str, priority: str = "default", tags: str = "") -> None:
    print(f"[notify:{priority}] {title}: {message}")
    if not NTFY_TOPIC:
        print("  (NTFY_TOPIC not set, skipping push)")
        return
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title, "Priority": priority, "Tags": tags},
            timeout=20,
        ).raise_for_status()
    except requests.RequestException as e:
        print(f"  failed to send ntfy push: {e}", file=sys.stderr)


def fetch_events() -> dict:
    url = TIMEEDIT_URL.split("#")[0]
    if url.endswith(".html"):
        url = url[: -len(".html")] + ".json"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    events = {}
    for r in data["reservations"]:
        cols = r.get("columns", [])

        def col(i):
            return cols[i].strip() if i < len(cols) else ""

        events[r["id"]] = {
            "course": col(COL_COURSE) or col(COL_ACTIVITY) or "(unknown)",
            "activity": col(COL_ACTIVITY),
            "date": r["startdate"],
            "start": r["starttime"],
            "end": r["endtime"],
            "room": col(COL_ROOM),
            "teacher": col(COL_TEACHER),
            "comment": col(COL_COMMENT),
        }
    return events


def parse_date(d: str) -> date:
    return datetime.strptime(d, "%d.%m.%Y").date()


def fmt(ev: dict) -> str:
    day = WEEKDAYS[parse_date(ev["date"]).weekday()]
    return f"{day} {ev['date']} {ev['start']}–{ev['end']}"


def is_future(ev: dict) -> bool:
    return parse_date(ev["date"]) >= date.today()


def is_cancelled(ev: dict) -> bool:
    text = f"{ev['activity']} {ev['comment']} {ev['course']}".lower()
    return any(m in text for m in CANCEL_MARKERS)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"events": None, "consecutive_failures": 0}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def diff_and_notify(old: dict, new: dict) -> None:
    for eid, ev in new.items():
        prev = old.get(eid)
        if prev is None:
            if is_future(ev):
                notify(f"New event: {ev['course']}", f"{fmt(ev)} in {ev['room']}", "default", "calendar")
            continue
        if is_cancelled(ev) and not is_cancelled(prev):
            notify(f"CANCELLED: {ev['course']}", f"{fmt(ev)} — {ev['comment'] or ev['activity']}", "max", "x,warning")
            continue
        if (prev["date"], prev["start"], prev["end"]) != (ev["date"], ev["start"], ev["end"]):
            if is_future(ev) or is_future(prev):
                notify(
                    f"Time changed: {ev['course']}",
                    f"{fmt(prev)} → {fmt(ev)} (room {ev['room']})",
                    "high",
                    "warning,clock",
                )
        elif prev["room"] != ev["room"] and is_future(ev):
            notify(f"Room changed: {ev['course']}", f"{fmt(ev)}: {prev['room']} → {ev['room']}", "default", "door")

    for eid, prev in old.items():
        if eid not in new and is_future(prev):
            notify(
                f"REMOVED (likely cancelled): {prev['course']}",
                f"{fmt(prev)} in {prev['room']} disappeared from the schedule",
                "max",
                "x,warning",
            )


def main() -> int:
    state = load_state()
    try:
        events = fetch_events()
    except Exception as e:
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        print(f"fetch/parse failed ({state['consecutive_failures']} in a row): {e}", file=sys.stderr)
        if state["consecutive_failures"] == 2:
            notify("Schedule checker is broken", f"Failed to fetch TimeEdit twice in a row: {e}", "high", "rotating_light")
        save_state(state)
        return 1

    state["consecutive_failures"] = 0
    if state.get("events") is None:
        print(f"First run: saved baseline with {len(events)} events, no notifications.")
    else:
        diff_and_notify(state["events"], events)
        print(f"Checked {len(events)} events against snapshot of {len(state['events'])}.")
    state["events"] = events
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
