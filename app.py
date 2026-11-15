"""Crack or Track by Abo Sara — web application."""

import time
from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db
import engine
from content import BY_ID, MISSIONS

app = FastAPI(title="Crack or Track by Abo Sara")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.init()


def context(request, **extra):
    player = db.player()
    rank = engine.rank_for(player["xp"])
    nxt, nxt_name = engine.next_rank(player["xp"])
    ctx = {"player": player, "rank": rank, "next_threshold": nxt,
           "next_rank": nxt_name, "missions": MISSIONS}
    ctx.update(extra)
    return ctx


def track_stats(player_id):
    prog = db.progress_map(player_id)
    stats = {}
    for track in ("red", "blue", "both"):
        items = [m for m in MISSIONS if m["track"] == track]
        done = sum(1 for m in items if prog.get(m["id"], {}).get("attempts"))
        stats[track] = {"done": done, "total": len(items)}
    return stats, prog


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    player = db.player()
    stats, prog = track_stats(player["id"])
    activity = db.recent_activity(player["id"])
    achievement_list = db.achievements(player["id"], MISSIONS)
    daily = MISSIONS[date.today().toordinal() % len(MISSIONS)]
    completed = sum(1 for m in MISSIONS if prog.get(m["id"], {}).get("attempts"))
    scores = [p["best_score"] for p in prog.values()]
    average = round(sum(scores) / len(scores)) if scores else 0
    return templates.TemplateResponse(
        request, "dashboard.html",
        context(request, active="dashboard", stats=stats, prog=prog,
                activity=activity, achievements=achievement_list, daily=daily,
                completed=completed, average=average),
    )


@app.get("/missions", response_class=HTMLResponse)
def missions_page(request: Request, track: str = ""):
    player = db.player()
    stats, prog = track_stats(player["id"])
    items = [m for m in MISSIONS if not track or m["track"] == track]
    return templates.TemplateResponse(
        request, "missions.html",
        context(request, active=track or "all", items=items, prog=prog, stats=stats),
    )


@app.get("/mission/{mid}", response_class=HTMLResponse)
def mission_page(request: Request, mid: str):
    mission = BY_ID.get(mid)
    if not mission:
        return HTMLResponse("Mission not found", status_code=404)
    state = {"stage": 0, "score": 0.0, "wrong": 0, "hints": 0,
             "started": time.time()}
    return render_stage(request, mission, state)


def render_stage(request, mission, state, hints_shown=None):
    idx = int(state["stage"])
    stage = mission["stages"][idx]
    return templates.TemplateResponse(
        request, "mission.html",
        context(request, active=mission["track"], m=mission, stage=stage,
                idx=idx, state=state,
                hints_shown=state["hints"] if hints_shown is None else hints_shown,
                hint_list=mission["hints"][:state["hints"]]),
    )


def state_from_form(form):
    return {
        "stage": int(form.get("stage", 0)),
        "score": float(form.get("score", 0)),
        "wrong": int(form.get("wrong", 0)),
        "hints": min(4, int(form.get("hints", 0))),
        "started": float(form.get("started", time.time())),
    }


@app.post("/mission/{mid}/submit", response_class=HTMLResponse)
async def submit(request: Request, mid: str):
    mission = BY_ID.get(mid)
    if not mission:
        return HTMLResponse("Mission not found", status_code=404)
    form = await request.form()
    return handle_submit(request, mission, form)


@app.post("/mission/{mid}/hint", response_class=HTMLResponse)
async def hint(request: Request, mid: str):
    mission = BY_ID.get(mid)
    form = await request.form()
    state = state_from_form(form)
    state["hints"] = min(4, state["hints"] + 1)
    return render_stage(request, mission, state)


@app.post("/mission/{mid}/continue", response_class=HTMLResponse)
async def cont(request: Request, mid: str):
    mission = BY_ID.get(mid)
    form = await request.form()
    state = state_from_form(form)
    state["stage"] = int(form.get("next", 0))
    return render_stage(request, mission, state)


def handle_submit(request, mission, form):
    state = state_from_form(form)
    idx = state["stage"]
    stage = mission["stages"][idx]
    points, ok, explain = engine.evaluate(stage, form)
    state["score"] += points
    if not ok:
        state["wrong"] += 1

    if idx + 1 >= len(mission["stages"]):
        elapsed = max(0, time.time() - state["started"])
        result = engine.mission_score(
            mission["stages"], state["score"], state["wrong"], state["hints"],
            mission["difficulty"], mission["minutes"], elapsed,
        )
        db.save_attempt(db.player()["id"], mission["id"],
                        result["score"], result["xp"])
        return templates.TemplateResponse(
            request, "result.html",
            context(request, active=mission["track"], m=mission, result=result,
                    elapsed=round(elapsed), state=state, ok=ok, explain=explain),
        )

    return templates.TemplateResponse(
        request, "feedback.html",
        context(request, active=mission["track"], m=mission, ok=ok,
                explain=explain, next_idx=idx + 1, state=state),
    )
