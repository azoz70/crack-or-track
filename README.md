# Crack or Track by Abo Sara

A cybersecurity training game with two tracks: **Red Team operations** and
**SOC operations**. Learn how attackers find weaknesses, and how defenders
detect and respond — in the same product.

All scenarios use fictional hosts, logs, and credentials. Nothing in the game
touches a real network.

## Features

- **Two tracks** — Red Team (recon, web, API) and SOC (phishing, SIEM, malware)
- **Red vs SOC crossover mission** — see the same intrusion from both sides
- **Interactive stages** — analyze real-looking output, type commands, make
  decisions, and write findings; no multiple-choice-only quizzes
- **Progressive hints** — four levels per mission, at a score cost
- **XP, ranks, achievements** — progress saved in SQLite
- **Scoring that rewards thinking** — accuracy, methodology (wrong answers),
  efficiency (hints), and time
- **Dark operations console UI** — dashboard, track progress, recent activity

## Quick start

```bash
cd breach
python3 -m venv .venv
./.venv/bin/pip install fastapi "uvicorn[standard]" jinja2 python-multipart
./run.sh
```

Open **http://127.0.0.1:8800**.

## Missions

| ID | Track | Title | Category |
|---|---|---|---|
| r1 | Red | Silent Recon | Reconnaissance |
| r2 | Red | Broken Login | Web application |
| r3 | Red | Object Lesson | API security |
| b1 | SOC | The Urgent Invoice | Phishing analysis |
| b2 | SOC | Impossible Travel | SIEM investigation |
| b3 | SOC | Encoded Payload | Malware analysis |
| x1 | Both | Suspicious Activity Detected | Red vs SOC |

## Scoring

| Component | Effect |
|---|---|
| Correct stage | contributes accuracy |
| Wrong answer | −4 points each |
| Hint revealed | −6 points each |
| Finish within estimate | +10 points |

Score is 0–100. XP = score × (1 + 0.25 × difficulty) + 10.

### Ranks

| XP | Rank |
|---|---|
| 0 | Cyber Rookie |
| 250 | Junior Analyst |
| 600 | Security Operator |
| 1000 | Red Team Operator |
| 1400 | SOC Specialist |
| 1900 | Senior Security Specialist |
| 2600 | Elite Cyber Operator |

## Architecture

```
app.py        FastAPI routes (dashboard, missions, stages, hints)
content.py    mission data — stages, options, hints, explanations
engine.py     evaluation, scoring, ranks
db.py         SQLite: players, progress, activity, achievements
templates/    Jinja pages (dark console UI)
static/       stylesheet
tests/        engine + content tests
breach.py     original CLI version (still playable)
```

Commands are evaluated by pure functions in `engine.py`, so scoring is
unit-tested without running the web server.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

42 tests: CLI engine, web scoring, rank thresholds, stage evaluation,
partial credit for reports, and mission content integrity.

## CLI version

The original terminal game still works:

```bash
python3 breach.py      # mission 1
./demo.sh              # scripted playthrough
```

## Disclaimer

Every host, credential, and log line is fictional. Real security testing
requires explicit written authorization.
