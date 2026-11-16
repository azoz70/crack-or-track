"""Crack or Track by Abo Sara — web application."""

import json
import time
from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import db
import engine
from content import BY_ID, MISSIONS, localize_mission
from i18n import get_strings

app = FastAPI(title="CRACK OR TRACK by Abo Sara")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.init()


def context(request, **extra):
    player = db.player()
    rank = engine.rank_for(player["xp"])
    nxt, nxt_name = engine.next_rank(player["xp"])
    lang = request.cookies.get("lang", "en")
    if lang not in ("en", "ar"):
        lang = "en"
    ctx = {"player": player, "rank": rank, "next_threshold": nxt,
           "next_rank": nxt_name, "missions": MISSIONS,
           "lang": lang, "S": get_strings(lang)}
    ctx.update(extra)
    return ctx


def lang_for(request):
    lang = request.cookies.get("lang", "en")
    return lang if lang in ("en", "ar") else "en"


def get_mission(mid, request):
    if mid not in BY_ID:
        return None
    return localize_mission(BY_ID[mid], lang_for(request))


def track_stats(player_id):
    prog = db.progress_map(player_id)
    stats = {}
    for track in ("red", "blue", "both"):
        items = [m for m in MISSIONS if m["track"] == track]
        done = sum(1 for m in items if prog.get(m["id"], {}).get("attempts"))
        stats[track] = {"done": done, "total": len(items)}
    return stats, prog


def question_stats():
    missions_list = []
    total = 0
    counts = {"red": 0, "blue": 0, "both": 0}
    for m in MISSIONS:
        n = len(m["stages"])
        total += n
        counts[m["track"]] = counts.get(m["track"], 0) + n
        missions_list.append({
            "id": m["id"], "title": m["title"], "count": n,
            "color": m["track"] if m["track"] != "both" else "purple",
        })
    return {"total": total, "red": counts["red"], "blue": counts["blue"],
            "purple": counts["both"], "mission_count": len(MISSIONS),
            "missions_list": missions_list}


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/lang/{new_lang}")
def set_lang(request: Request, new_lang: str):
    if new_lang not in ("en", "ar"):
        new_lang = "en"
    referer = request.headers.get("referer") or "/"
    resp = RedirectResponse(referer, status_code=303)
    resp.set_cookie("lang", new_lang, max_age=60 * 60 * 24 * 365, samesite="lax")
    return resp


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
                completed=completed, average=average, qbank=question_stats()),
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
    mission = get_mission(mid, request)
    if not mission:
        return HTMLResponse("Mission not found", status_code=404)
    state = {"stage": 0, "score": 0.0, "wrong": 0, "hints": 0,
             "started": time.time(), "results": []}
    return render_stage(request, mission, state)


def hint_levels_for(mission, stage):
    return (stage.get("hint_levels") or mission.get("hints") or [])[:3]


def render_stage(request, mission, state, hints_shown=None):
    idx = int(state["stage"])
    stage = mission["stages"][idx]
    levels = hint_levels_for(mission, stage)
    used = min(state["hints"], len(levels)) if hints_shown is None else hints_shown
    return templates.TemplateResponse(
        request, "mission.html",
        context(request, active=mission["track"], m=mission, stage=stage,
                idx=idx, state=state,
                hints_shown=used, hint_list=levels[:used], hint_count=len(levels)),
    )


def state_from_form(form):
    return {
        "stage": int(form.get("stage", 0)),
        "score": float(form.get("score", 0)),
        "wrong": int(form.get("wrong", 0)),
        "hints": min(3, int(form.get("hints", 0))),
        "started": float(form.get("started", time.time())),
        "results": json.loads(form.get("results") or "[]"),
    }


@app.post("/mission/{mid}/submit", response_class=HTMLResponse)
async def submit(request: Request, mid: str):
    mission = get_mission(mid, request)
    if not mission:
        return HTMLResponse("Mission not found", status_code=404)
    form = await request.form()
    return handle_submit(request, mission, form)


@app.post("/mission/{mid}/hint", response_class=HTMLResponse)
async def hint(request: Request, mid: str):
    mission = get_mission(mid, request)
    form = await request.form()
    state = state_from_form(form)
    stage = mission["stages"][int(state["stage"])]
    levels = hint_levels_for(mission, stage)
    state["hints"] = min(len(levels), state["hints"] + 1)
    return render_stage(request, mission, state)


@app.post("/mission/{mid}/continue", response_class=HTMLResponse)
async def cont(request: Request, mid: str):
    mission = get_mission(mid, request)
    form = await request.form()
    state = state_from_form(form)
    state["stage"] = int(form.get("next", 0))
    return render_stage(request, mission, state)


def selected_text(form, stage):
    kind = stage.get("type")
    if kind == "decision":
        return ",".join(sorted(form.getlist("answer")))
    if kind == "report":
        return f"severity={form.get('severity')};remediation={form.get('remediation')}"
    return str(form.get("answer", ""))


def compute_xp_delta(player_id, mission, result):
    """Award full XP on first completion, only the improvement delta on replay."""
    row = db.get_mission_progress(player_id, mission["id"])
    if row is None:
        return result["xp"]
    old_best = row["best_score"]
    if result["score"] > old_best:
        return max(0, result["xp"] - engine.xp_for(old_best, mission["difficulty"]))
    return 0


def correct_answer_text(stage):
    kind = stage.get("type", "")
    if kind == "true_false":
        return "True" if str(stage.get("correct", "")).strip().lower() in ("true", "1") else "False"
    if kind == "terminal":
        return " / ".join(stage.get("accept", []))
    if kind == "report":
        opts = stage.get("remediation_options", [])
        rem = int(stage.get("remediation", 0))
        return f"{stage.get('severity', '')} · {opts[rem] if opts and rem < len(opts) else ''}"
    if kind in engine.MULTI_TYPES:
        opts = stage.get("options", [])
        return ", ".join(opts[i] for i in stage.get("correct", []) if i < len(opts))
    opts = stage.get("options", [])
    c = stage.get("correct")
    if opts:
        try:
            return opts[int(c)]
        except (ValueError, TypeError, IndexError):
            return str(c)
    return str(c)


def next_mission_for(mission):
    same = [m for m in MISSIONS if m["id"] != mission["id"] and m["track"] == mission["track"]]
    pool = same or [m for m in MISSIONS if m["id"] != mission["id"]]
    for diff in (mission["difficulty"], mission["difficulty"] + 1):
        hit = [m for m in pool if m["difficulty"] == diff]
        if hit:
            return hit[0]
    return pool[0] if pool else None


def build_report(mission, state, result, elapsed):
    results = state.get("results", [])
    total = len(results)
    correct = sum(1 for r in results if r.get("ok"))
    incorrect = total - correct
    skills = {}
    for r in results:
        s = r.get("skill") or "General"
        bucket = skills.setdefault(s, {"correct": 0, "total": 0})
        bucket["total"] += 1
        if r.get("ok"):
            bucket["correct"] += 1
    def _color(name):
        for track, names in engine.SKILLS.items():
            if name in names:
                return track
        return "purple"

    skill_rows = sorted(
        [{"skill": k, "correct": v["correct"], "total": v["total"],
          "pct": round(v["correct"] * 100 / v["total"]) if v["total"] else 0,
          "color": _color(k)}
         for k, v in skills.items()],
        key=lambda x: x["pct"],
    )
    strongest = [s for s in reversed(skill_rows) if s["pct"] >= 70][:3]
    weakest = [s for s in skill_rows if s["pct"] < 70][:3]
    mistakes = [r for r in results if not r.get("ok")]
    recs = []
    if weakest:
        recs.append("Focus on: " + ", ".join(s["skill"] for s in weakest))
    if mistakes:
        recs.append(f"Review {len(mistakes)} incorrect answer(s) in Review mode")
    if not weakest and not mistakes:
        recs.append("Strong run — try a harder mission")
    recs.append("Retry with no hints to confirm mastery")
    return {
        "score": result["score"], "xp": result["xp"], "accuracy": result["accuracy"],
        "correct": correct, "incorrect": incorrect, "total": total,
        "time": round(elapsed), "difficulty": mission["difficulty"],
        "skills": skill_rows, "strongest": strongest, "weakest": weakest,
        "mistakes": mistakes, "recommendations": recs,
        "next_mission": next_mission_for(mission),
        "penalty": result["penalty"], "time_bonus": result["time_bonus"],
    }


def handle_submit(request, mission, form):
    state = state_from_form(form)
    idx = state["stage"]
    stage = mission["stages"][idx]
    points, ok, explain = engine.evaluate(stage, form)
    state["score"] += points
    if not ok:
        state["wrong"] += 1

    player_id = db.player()["id"]
    skill = engine.skill_for(mission, stage)
    db.record_question_attempt(
        player_id, mission["id"], idx, stage.get("type", ""),
        skill, selected_text(form, stage), ok, points, state["hints"],
    )
    state.setdefault("results", []).append({
        "idx": idx, "ok": ok, "points": points, "skill": skill,
        "prompt": stage.get("prompt", ""), "title": stage.get("title", ""),
        "explain": explain,
    })

    if idx + 1 >= len(mission["stages"]):
        elapsed = max(0, time.time() - state["started"])
        result = engine.mission_score(
            mission["stages"], state["score"], state["wrong"], state["hints"],
            mission["difficulty"], mission["minutes"], elapsed,
        )
        xp_delta = compute_xp_delta(player_id, mission, result)
        db.save_attempt(player_id, mission["id"], result["score"], xp_delta)
        result["xp"] = xp_delta
        report = build_report(mission, state, result, elapsed)
        db.save_mission_report(player_id, mission["id"], report)
        return templates.TemplateResponse(
            request, "result.html",
            context(request, active=mission["track"], m=mission, result=result,
                    elapsed=round(elapsed), state=state, ok=ok, explain=explain,
                    report=report),
        )

    return templates.TemplateResponse(
        request, "feedback.html",
        context(request, active=mission["track"], m=mission, ok=ok,
                explain=explain, next_idx=idx + 1, state=state,
                stage=stage, skill=skill, correct_answer=correct_answer_text(stage)),
    )


@app.get("/review", response_class=HTMLResponse)
def review(request: Request):
    player = db.player()
    skills = db.skill_stats(player["id"])
    reports = []
    for r in db.recent_reports(player["id"], limit=10):
        try:
            d = json.loads(r["data"])
        except Exception:
            d = {}
        reports.append({"id": r["id"], "mission_id": r["mission_id"],
                        "score": d.get("score"), "created": r["created"]})
    incorrect = []
    for a in db.question_history(player["id"], incorrect_only=True, limit=30):
        m = get_mission(a["mission_id"], request)
        if not m:
            continue
        stages = m["stages"]
        if 0 <= a["stage_index"] < len(stages):
            st = stages[a["stage_index"]]
            incorrect.append({"mission_id": a["mission_id"], "mission_title": m["title"],
                              "stage_index": a["stage_index"],
                              "prompt": st.get("prompt", ""), "title": st.get("title", "")})
    return templates.TemplateResponse(
        request, "review.html",
        context(request, active="review", skills=skills, reports=reports, incorrect=incorrect),
    )


@app.get("/report/{report_id}", response_class=HTMLResponse)
def report_view(request: Request, report_id: int):
    row = db.get_report(report_id)
    if not row:
        return HTMLResponse("Report not found", status_code=404)
    data = json.loads(row["data"])
    m = get_mission(row["mission_id"], request)
    return templates.TemplateResponse(
        request, "report.html",
        context(request, active="review", m=m, report=data),
    )


@app.get("/review/practice/{mid}/{stage_index}", response_class=HTMLResponse)
def practice_get(request: Request, mid: str, stage_index: int):
    m = get_mission(mid, request)
    if not m or not (0 <= stage_index < len(m["stages"])):
        return HTMLResponse("Question not found", status_code=404)
    return templates.TemplateResponse(
        request, "practice.html",
        context(request, active="review", m=m, stage=m["stages"][stage_index],
                idx=stage_index, result=None),
    )


@app.post("/review/practice/{mid}/{stage_index}", response_class=HTMLResponse)
async def practice_post(request: Request, mid: str, stage_index: int):
    m = get_mission(mid, request)
    if not m or not (0 <= stage_index < len(m["stages"])):
        return HTMLResponse("Question not found", status_code=404)
    stage = m["stages"][stage_index]
    form = await request.form()
    _, ok, explain = engine.evaluate(stage, form)
    return templates.TemplateResponse(
        request, "practice.html",
        context(request, active="review", m=m, stage=stage, idx=stage_index,
                result={"ok": ok, "explain": explain,
                        "skill": engine.skill_for(m, stage),
                        "correct": correct_answer_text(stage)}),
    )
