#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
radar.py - from a saved video to a card tied to your projects.

Usage:
    python3 radar.py new.json              # triage + write cards
    python3 radar.py questions             # print the three Jev questions (JSON)
    python3 radar.py states new.json       # print the per-video state objects for Jev
    python3 radar.py init                  # create the radar folder with an example projects.json

Folder (env RADAR_DIR, default ./radar):
    projects.json   your projects: the list that decides "what is this video FOR"
    seen.json       every video already processed (id -> verdict), never cleared
    cards/          one Markdown card per video that passed the threshold

new.json: [{"id":"...","title":"...","channel":"...","text":"transcript or description",
            "jev": {"usefulness": 0-3, "project": "...", "action": true}}]   # "jev" optional

Scoring:
    If "jev" is present in the item, it is used as is (Claude or another tool judged it).
    Otherwise, if a Jev key is configured, Jev is called (cents per thousand videos).
    Otherwise the script stops and tells you to add "jev" yourself.
    usefulness 0-3 becomes 0-100; below RADAR_THRESHOLD (default 45) no card is written.
"""

import json
import os
import sys
import datetime
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jev  # noqa: E402

RADAR = os.path.abspath(os.environ.get("RADAR_DIR", "radar"))
CARDS = os.path.join(RADAR, "cards")
SEEN = os.path.join(RADAR, "seen.json")
PROJECTS = os.path.join(RADAR, "projects.json")
THRESHOLD = int(os.environ.get("RADAR_THRESHOLD", "45"))


def questions(projects):
    return {
        "usefulness": {
            "type": "score",
            "instructions": "Read `video.title` and `video.transcript`. How useful is it to the person described in `profile`?",
            "criteria": [
                {"summary": "Pure entertainment, teaches nothing"},
                {"summary": "Interesting curiosity, no application"},
                {"summary": "Good idea, applicable in months"},
                {"summary": "Concrete thing they can try this week"},
            ],
        },
        "project": {
            "type": "choice",
            "instructions": "Which project does the video in `video` serve? If none, choose the 'no project' option.",
            "criteria": {p["name"]: {"what": p["what"]} for p in projects},
        },
        "action": {
            "type": "noul",
            "instructions": "Is there something concrete in `video` to do or try within a week?",
            "criteria": {"true": "Names a step that can be done now", "false": "Only theory or inspiration"},
        },
    }


def state(v, profile):
    return {"profile": profile,
            "video": {"title": v.get("title", ""), "channel": v.get("channel", ""),
                      "transcript": v.get("text", "")[:20000]}}


def load(p, empty):
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return empty


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:60] or "video"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    if cmd == "init":
        os.makedirs(CARDS, exist_ok=True)
        if not os.path.isfile(PROJECTS):
            shutil.copy(os.path.join(HERE, "..", "templates", "projects.example.json"), PROJECTS)
        if not os.path.isfile(SEEN):
            json.dump({}, open(SEEN, "w"))
        print("radar folder ready:", RADAR)
        print("edit", PROJECTS, "with YOUR projects before the first run")
        return 0

    proj = load(PROJECTS, {})
    projects = proj.get("projects", [])
    profile = proj.get("profile", "a person who wants to turn what they watch into work on their own projects")
    if not projects:
        print("no projects.json in", RADAR, "- run: python3 radar.py init")
        return 2

    if cmd == "questions":
        print(json.dumps(questions(projects), ensure_ascii=False))
        return 0
    if cmd == "states" and len(sys.argv) > 2:
        print(json.dumps({v["id"]: state(v, profile) for v in load(sys.argv[2], [])}, ensure_ascii=False))
        return 0

    new = load(cmd, [])
    seen = load(SEEN, {})
    os.makedirs(CARDS, exist_ok=True)
    none_name = next((p["name"] for p in projects if p.get("id") == "none"), "No project")
    done, dropped = [], []

    for v in new:
        if v["id"] in seen:
            continue
        if isinstance(v.get("jev"), dict):
            r = v["jev"]
        else:
            try:
                r = jev.ask(state(v, profile), questions(projects))["answers"]
            except jev.JevError as e:
                print("Jev not available:", e)
                print("Add a \"jev\" field to each item ({usefulness: 0-3, project, action}) and run again.")
                return 3
        try:
            score = int(round(float(r.get("usefulness", 0)) / 3 * 100))
        except (TypeError, ValueError):
            score = 0
        project = r.get("project") or none_name
        action = bool(r.get("action"))
        today = datetime.date.today().isoformat()
        row = {"id": v["id"], "title": v.get("title", ""), "channel": v.get("channel", ""),
               "score": score, "project": project, "action": action, "date": today}
        seen[v["id"]] = row
        if score < THRESHOLD:
            dropped.append(row)
            continue
        name = "%s-%s.md" % (today, slug(v.get("title", v["id"])))
        with open(os.path.join(CARDS, name), "w", encoding="utf-8") as f:
            f.write("# %s\n\n" % v.get("title", ""))
            f.write("- Channel: %s\n- Link: https://youtu.be/%s\n" % (v.get("channel", ""), v["id"]))
            f.write("- Project: %s\n- Usefulness: %d/100\n- Action within 7 days: %s\n\n" %
                    (project, score, "yes" if action else "no"))
            f.write("## What it says\n\n(to be written by Claude)\n\n")
            f.write("## Why it matters to me\n\n(to be written by Claude)\n\n")
            f.write("## What I do\n\n1. \n2. \n\n")
            f.write("## Transcript\n\n%s\n" % v.get("text", "")[:20000])
        done.append(row)

    with open(SEEN, "w", encoding="utf-8") as f:
        json.dump(seen, f, ensure_ascii=False, indent=1)
    print(json.dumps({"cards": done, "dropped": dropped}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
