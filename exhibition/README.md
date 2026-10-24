# The al-Marṣad exhibition

Eight halls, about 24 minutes, for a meeting with a scholar. It runs from this laptop with no
internet: the Sky Atlas and the Badr expedition appear inside the halls as live views, served from
this machine.

## Start

```bash
python3 exhibition/serve.py
```

It opens `http://127.0.0.1:8770/exhibition/` in the browser. Press **F** for full screen. On a TV,
set the browser zoom to 125–150%. If the port is busy: `python3 exhibition/serve.py --port 8771`.

Your name on the opening and closing screens: copy `exhibition/presenter.example.json` to
`exhibition/presenter.local.json` and fill in `name`, `role` and `contact`. That file is
git-ignored; never commit it. Without it the line stays blank.

Before he sits down: walk once to hall 4 and back (**Home**), so both live views have drawn.

## Keys

| Key | What it does |
|---|---|
| → PageDown Space | next hall |
| ← PageUp | previous hall |
| 1–8, Home, End | jump to a hall |
| P | the presenter notes on this screen (for rehearsal) |
| Notes window (button at the bottom right) | the notes in their own window, for a second screen; the two windows follow each other |
| T | the timer; Shift+T restarts it at 00:00 |
| F | full screen |
| S | a still picture in place of the live view, and back |
| Esc | closes the full view, hands the keys back from inside a live view, or closes the notes |

**The timer** starts by itself when you leave the opening, already counting the opening's minute;
press T on the opening to start it there instead. It shows the hall's planned minutes, says
"running long" a minute past them, and from minute 20 tells you to begin the requests (hall 7).

**Live views.** Inside the Atlas, PageDown still moves the walk on. Inside the halaqa room the arrow
keys and PageDown step the room: press Esc first, then PageDown. If a live view has not drawn
within 12 seconds, its still picture takes its place by itself; press S to try the live view again.

## The walk

| Hall | Plan | Clock | Show | Say, in short |
|---|---|---|---|---|
| 1 Opening | 1 min | 0:00 | the screen, already up | Bismillāh. Who you are, in one sentence. Built by one maintainer with AI help; nothing reviewed by a scholar yet, and that is why you have come. You will end with three requests. |
| 2 Why al-Marṣad | 2 min | 1:00 | the screen | Read the three lines slowly; let the "will not" lines stand. Say the AI part plainly: AI helped draw the statements from the text and wrote the glosses; nothing is accepted until a scholar accepts it. |
| 3 The sky of the Sīra | 6 min | 3:00 | the three buttons in order: **The central light**, **One record: Khadīja** (رضي الله عنها), **The Sīra in the order of the text** (let two stops play) | The Prophet ﷺ is the light at the centre, never a figure. The order and brightness carry no judgement of anyone. "Name records": one person can appear under several names until a scholar answers. |
| 4 Badr | 5 min | 9:00 | **The eve of Badr** (drag the time slider), **Which Friday?** (press "Check against the moon"), **The halaqa room** (click once inside, step with the arrows; Esc, then PageDown to leave) | The sky is computed, not painted. The text says Friday, the seventeenth of Ramaḍān; our simple crescent rule gives no Friday in any of the three candidate months ("None agrees"). We do not correct the text: we bring the question to a scholar. |
| 5 Where a report comes from | 3 min | 14:00 | the screen, top to bottom | One statement, its book and page, its chain as the text gives it, its status, and who may rule. The English line is a machine gloss, not a translation. Grading is his, not ours. |
| 6 What is built, what waits | 2 min | 17:00 | the screen; start with the zero | Everything shown is proposed; not one statement is reviewed. The pilot pack is ready and needs one scholar; say it is drawn from the 50 Stories, which an AI wrote. |
| 7 What we hope for | 4 min | 19:00, by 20:00 at the latest | the screen | Three requests, the first small and dated. The credit rule in its own words. Then stop, and listen. Agree one next step with a date. |
| 8 Close | 1 min | 23:00 | the screen; hand over the printed page | Thanks, the next step and its date. Jazākum Allāhu khayran. |

**Don't click** in the Atlas: the Ask and Merges tabs (new, and not part of this walk), Map, Globe and Time (few places and dates yet), a search for "Abū
Bakr" (it shows duplicates), the Arabic interface (a draft), "The turning" and the dark-mark legend.
In the expedition: "Who was there" (its wording is under review). The full notes for each hall,
with the likely questions and their answers, are under **P**.

## The printed page

Open `http://127.0.0.1:8770/exhibition/leave-behind.html` and print it on A4: it is one page.

## If something goes wrong

- A live view stays blank or stalls: press **S** for its still picture.
- The keys stop answering: the keys are inside a live view; press **Esc**.
- Each walk asks the Badr questions afresh: the page clears a rehearsal's Badr predictions when
  the expedition opens (only on this exhibition's address).

## For maintainers

- Every figure on the halls and the printed page is a `data-n` or `data-t` key filled from
  `numbers.js`, which `build.py` writes from the data:
  `.venv/bin/python exhibition/build.py --queue review/dist/queue.json` (add `--check` to compare only).
- The check: `node exhibition/check.cjs` (Playwright and Chromium; `scripts/check_all.sh` runs it).
  It walks every hall at 1920 × 1080 and 1280 × 800.
- The still pictures: `node exhibition/check.cjs --stills` rewrites `stills/` from the live views.
- Nothing is fetched from outside the machine: system fonts only, and `serve.py` listens on
  127.0.0.1 and never serves a dot folder or a folder listing.
