# Saved Video Radar

You save videos on YouTube and never open them again. This plugin turns each saved video
into a one-page card: what it says, why it matters to **your** projects, and the next two
actions — then the video goes back to you as work, not as a playlist entry.

## Use it

1. Install the plugin and ask Claude: "run my video radar" or "go through what I saved this week".
2. On the first run Claude creates a `radar/` folder with `projects.json`. Fill it with your
   own projects (5-10 lines: name + a few keywords). This list is what decides what each
   video is *for*.
3. Give Claude a playlist link, a list of links, or let it read your Watch Later / liked
   videos through a browser tool. It reads descriptions first, pulls transcripts only for
   the videos that pass the filter, and writes one Markdown card per video in `radar/cards/`.
4. Every processed video is recorded in `radar/seen.json`, so the next run only looks at
   what is new.

Triage can run on [Jev by TypeSafe](https://typesafe.ai) (a decision model: yes/no, choice,
score — about $0.00004 per video via OpenRouter) or, with no key at all, on Claude itself.

## What it contains

- `skills/saved-video-radar/SKILL.md` — the method Claude follows.
- `scripts/radar.py` — triage, `seen.json`, card writing (Python 3, no dependencies).
- `scripts/jev.py` — a tiny client for Jev's `/v1/systemone` endpoint (OpenRouter or TypeSafe).
- `templates/projects.example.json` — a starting projects file.

## Data

Video ids, titles, descriptions and transcripts are read from YouTube (public pages, your
own browser session for private playlists, or a transcript service you choose). If you
configure a Jev key, title and transcript of each video are sent to OpenRouter or TypeSafe
for scoring. Nothing else leaves your machine; the plugin stores its files in your `radar/`
folder and never deletes anything or edits your playlists.

## License

MIT.
