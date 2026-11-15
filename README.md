# BREACH — terminal hacking simulator

A small, dependency-free Python game about **authorized** red-team work:
scan a scope, find credentials, pivot through hosts, and grab the flag
before the detection meter hits 100%.

Playable in any terminal. Pure standard library. Runs offline.

## Why this exists

Most "hacking games" are quizzes. This one models the actual loop:
**recon → access → evidence → objective**, with a risk cost attached to
every noisy action. The detection meter is the point: speed matters, but
carelessness ends the engagement.

## Quick start

```bash
python3 breach.py        # Mission 1
python3 breach.py 2      # Mission 2
python3 breach.py 3      # Mission 3
```

No dependencies. Python 3.10+.

## Commands

| Command | Effect | Heat |
|---|---|---|
| `scan` | list hosts in scope | +5 |
| `connect <ip>` | open a session | +2 |
| `login <ip> <user> <pass>` | authenticate | +2 (+10 on failure) |
| `exploit <ip>` | use a known weakness | +20 |
| `ls` | list files | +1 |
| `cat <file>` | read a file | +2 |
| `flag` | submit the objective | +15 |
| `heat` | show detection level | 0 |
| `exit` | quit | 0 |

At 100% heat the SOC catches you and the engagement ends.

## Walkthrough (spoiler)

<details>
<summary>Mission 1 solution path</summary>

```
scan
connect 10.10.10.10
cat index.html          # leftover backup credentials
login 10.10.10.20 admin Sunshine2024
ls
cat flag.txt
flag
```

Total heat: ~18%. Clean run.

</details>

## Design

```
breach.py
├── MISSIONS      data-only mission definitions (hosts, creds, files, flag)
├── Game          state: heat, current host, files read, command count
│   ├── execute() one command → output text (no I/O, fully testable)
│   └── run()     terminal loop, prints, handles Win/Caught/Quit
└── save_score()  appends results to ~/.breach_scores.json
```

The engine has **no `print` inside command handlers** — `execute()` returns
text, `run()` prints it. That separation is what makes the tests possible.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Covers: recon, access control, credential handling, file reads, objective
gating, heat cap, mission 3 exploit path, and parser edge cases.

## Engineering notes — what I learned building this

1. **Separate the engine from the terminal.** `execute()` returns text; `run()`
   prints it. That single decision made 22 tests possible and would let a web
   front-end drop in later without touching the game logic.
2. **Missions are data, not code.** Adding a mission means adding a dict — no
   engine changes. Content and logic stay independent.
3. **Game-over is an exception, not a flag.** `Win`, `Caught`, and `Quit` unwind
   through one exit path, so no handler can silently continue after the
   engagement ends.
4. **Detection is a design constraint.** The heat meter forces the player to
   think about noise: every scan, failed login, and exploit costs something.
   That is the same trade-off as a real engagement.
5. **No randomness.** Deterministic missions mean reproducible tests and fair
   speed-runs.
6. **Zero dependencies.** Standard library only: clone and run in one command.

## Recording a demo

```bash
# scripted playthrough, no recording
./demo.sh

# record a cast file and convert it to a GIF
./record.sh
```

`record.sh` wraps `asciinema rec` and `agg` (install with
`brew install asciinema agg`). Commit `demo.gif` and reference it near the top:

```markdown
![demo](demo.gif)
```

## Roadmap

- [x] Three missions
- [x] Deterministic engine with 22 unit tests
- [x] Demo and recording scripts
- [ ] More missions (web, AD-style chain, API)
- [ ] Score table rendering
- [ ] Optional web front-end (FastAPI + xterm.js)
- [ ] Save/resume per mission

## Disclaimer

All hosts, credentials, and flags are fictional. This is a simulation.
Real testing requires explicit written authorization.
