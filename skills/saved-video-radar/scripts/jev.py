#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jev.py - micro-decisions with Jev by TypeSafe (typesafe.ai).

Jev is NOT a chat model: it writes no text and does not answer chat-completion
SDKs. It has its own endpoint, /v1/systemone, that takes a "state" (the thing
to judge) and one or more typed questions:

  noul   -> yes/no, returned as a probability 0-1
  choice -> one of the options you describe
  score  -> a level on a scale you describe

All questions go in ONE call: same input cost, several answers.

Two routes, tried in this order:
  1. OpenRouter   POST https://openrouter.ai/api/v1/systemone   model typesafe/jev-1.13
     key: the OPENROUTER_API_KEY environment variable (set it yourself for the session)
  2. TypeSafe     POST https://api.typesafe.ai/v1/systemone     model jev-latest
     key: the TYPESAFE_API_KEY environment variable

Each key is sent only to its own vendor (OpenRouter or TypeSafe), as a Bearer header.
No key is read from files, stored, or printed.
"""

import json
import os
import urllib.request
import urllib.error

OR_URL = "https://openrouter.ai/api/v1/systemone"
TS_URL = "https://api.typesafe.ai/v1/systemone"
OR_MODEL = os.environ.get("JEV_OR_MODEL", "typesafe/jev-1.13")
TS_MODEL = os.environ.get("JEV_TS_MODEL", "jev-latest")


class JevError(Exception):
    pass


def route():
    """Return (url, model, key) for the first available route, or None."""
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return OR_URL, OR_MODEL, k
    k = os.environ.get("TYPESAFE_API_KEY")
    if k:
        return TS_URL, TS_MODEL, k
    return None


def ask(state, questions, timeout=60):
    """state: str or dict. questions: {name: {type, instructions, criteria}}.
    Returns {"answers": {name: value}, "raw": <provider output>, "usage": {...}}."""
    r = route()
    if not r:
        raise JevError("No Jev key found (OPENROUTER_API_KEY or TYPESAFE_API_KEY).")
    url, model, key = r
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key,
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise JevError("HTTP %s from %s: %s" % (e.code, url, e.read()[:300].decode("utf-8", "replace")))
    except urllib.error.URLError as e:
        raise JevError("Cannot reach %s: %s" % (url, e.reason))
    return simplify(data)


def simplify(data):
    """Flatten the provider output into plain values."""
    raw = data.get("answers") or data.get("results") or data.get("output") or data
    answers = {}
    if isinstance(raw, dict):
        for name, a in raw.items():
            if not isinstance(a, dict):
                answers[name] = a
                continue
            t = a.get("type")
            if t == "noul" or "noul" in a:
                answers[name] = float(a.get("noul", 0)) >= 0.5
            elif t == "choice" or "choice" in a:
                answers[name] = a.get("choice")
            elif t == "score" or "score" in a:
                answers[name] = a.get("score")
            else:
                answers[name] = a.get("value", a)
    return {"answers": answers, "raw": raw, "usage": data.get("usage", {})}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: jev.py '<state text>' '<questions json>'")
        sys.exit(1)
    print(json.dumps(ask(sys.argv[1], json.loads(sys.argv[2])), ensure_ascii=False, indent=1))
