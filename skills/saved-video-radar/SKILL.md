---
name: saved-video-radar
description: Turn the YouTube videos the user saved (Watch Later, liked videos, any playlist, or a pasted list of links) into one-page cards tied to their own projects. Use when the user asks to go through their saved videos, run their video radar, process a playlist, or asks "what did I save and what do I do with it".
---

# Saved Video Radar

A saved video that is never opened again is wasted time. This skill turns each one into a card:
what it says, why it matters to THIS user, and the next two actions.

Everything lives in a folder (default `./radar`, or the `RADAR_DIR` environment variable):
`projects.json` (the user's projects), `seen.json` (every video already processed), `cards/`.
The scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/saved-video-radar/scripts/`.

## 0. First run: the projects file

Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/saved-video-radar/scripts/radar.py" init`, then open
`radar/projects.json` with the user. It needs:

- `profile`: one sentence about who the user is and what they are building.
- `projects`: 5-10 entries `{id, name, what}`. `what` is a short list of keywords. Keep one entry
  with `id: "none"` for entertainment. This list is what decides "what is this video FOR":
  a vague list gives vague cards.

Ask the user for the list only if there is nothing to start from; otherwise draft it from
what you already know about them and let them correct it.

## 1. Get the videos

Take the list in the order that works, stop at the first that does:

1. **Links pasted by the user** — nothing to fetch, use them.
2. **Public playlist** — `yt-dlp --flat-playlist -J "<playlist url>"` gives id, title, channel,
   duration without downloading anything. Install with `pip install yt-dlp` if missing.
3. **Private playlist (Watch Later `WL`, Liked `LL`, a private list)** — needs the user's YouTube
   session, so use a browser tool, never the shell. Open `https://www.youtube.com/playlist?list=<id>`
   in the browser the session offers (Claude in Chrome or the built-in browser) and read the list
   from the page. Scrolling stops working past ~100 videos; for long lists call YouTube's own
   page API from the page's JavaScript: `POST /youtubei/v1/browse` with
   `{context: ytcfg.get('INNERTUBE_CONTEXT'), browseId: 'VL' + <playlist id>}`, headers
   `Authorization: SAPISIDHASH <ts>_<sha1("<ts> <SAPISID cookie> https://www.youtube.com")>`
   and `X-Goog-AuthUser: ytcfg.get('SESSION_INDEX')`. Videos are in `playlistVideoRenderer`
   or `lockupViewModel`; the next page is `{continuation: <first token in the response>}`.
   If the user has several Google accounts in the browser, `SESSION_INDEX` is what picks
   the right one: with the wrong value YouTube answers "playlist does not exist".

Skip every id already in `seen.json`. Deleted videos stay in YouTube's count but never appear:
it is normal that the numbers do not match.

## 2. Text of each video (cheap first)

The description alone is often enough to judge a video. Get it first, transcripts only for
the ones that pass the threshold:

- Description: `yt-dlp --skip-download --print description "<url>"`, or from the browser
  with `POST /youtubei/v1/player {context, videoId}` → `videoDetails.shortDescription`.
- Transcript: `pip install youtube-transcript-api` then
  `python3 -c "from youtube_transcript_api import YouTubeTranscriptApi as Y; print(' '.join(s['text'] for s in Y().fetch('<id>')))"`.
  If the network blocks youtube.com from the shell, use a transcript service the session
  offers (for example an Apify actor such as `starvibe/youtube-video-transcript`, input
  `{"youtube_url": "https://www.youtube.com/watch?v=<id>"}`), or ask the user to paste it.

Never download the video itself.

## 3. Triage: three questions, not a summary

For every video answer three questions: how useful (0-3), which project, is there an action
within a week. Two ways:

- **With Jev** (TypeSafe's decision model, ~$0.00004 per video): set `OPENROUTER_API_KEY`
  (model `typesafe/jev-1.13`) or `TYPESAFE_API_KEY`, write `new.json` as
  `[{"id","title","channel","text"}]` and run
  `python3 "${CLAUDE_PLUGIN_ROOT}/skills/saved-video-radar/scripts/radar.py" new.json`.
  The script asks Jev the three questions in one call per video.
  If the shell cannot reach openrouter.ai, get the questions with `radar.py questions` and the
  per-video states with `radar.py states new.json`, call the endpoint from wherever the
  network works, and put the answers back as a `"jev"` field on each item.
- **Without Jev**: judge the three questions yourself from title + description, write them as
  `"jev": {"usefulness": 0-3, "project": "<name from projects.json>", "action": true|false}`
  on each item, and run the same script. Be strict on usefulness: 3 means the user could
  try it this week, 0 means entertainment. Say in the final message that the triage was
  done by Claude, not by Jev.

The script converts 0-3 to 0-100, drops everything under 45 (change with `RADAR_THRESHOLD`),
updates `seen.json`, and writes one card per surviving video in `cards/`.

## 4. The part that counts: write the card

The script leaves three sections empty. Fill them by reading the transcript or description:

- **What it says** — max 8 lines, concrete, no enthusiasm. If it is a short with no useful
  speech, say so and use the description.
- **Why it matters to me** — the real link with the user's projects, their ongoing work, and
  what they already have. When they already own a piece of what the video shows, say it:
  it tells them how much is actually missing. This section is the whole point; a generic
  "this could be useful for your AI projects" is a failed card.
- **What I do** — max 2 points, concrete, each one doable this week. Mark with 🥊 the ones
  only the user can do in person.

## 5. Report

One line per card in the reply (title, project, what they get out of it). Dropped videos
are counted, not listed. End with ONE list of actions, max 2. Nothing is deleted and no
video is ever removed from a playlist.
