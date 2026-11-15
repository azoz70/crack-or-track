"""Scoring, ranks, and stage evaluation for Crack or Track."""

RANKS = [
    (0, "Cyber Rookie"),
    (250, "Junior Analyst"),
    (600, "Security Operator"),
    (1000, "Red Team Operator"),
    (1400, "SOC Specialist"),
    (1900, "Senior Security Specialist"),
    (2600, "Elite Cyber Operator"),
]


def norm(text):
    return " ".join((text or "").lower().split())


def rank_for(xp):
    name = RANKS[0][1]
    for threshold, title in RANKS:
        if xp >= threshold:
            name = title
    return name


def next_rank(xp):
    for threshold, title in RANKS:
        if xp < threshold:
            return threshold, title
    return None, None


def evaluate(stage, form):
    """Return (points 0..1, correct, explanation)."""
    kind = stage["type"]

    if kind == "analyze":
        answer = form.get("answer")
        ok = answer is not None and str(answer) == str(stage["correct"])
        return (1.0 if ok else 0.0), ok, stage["explain"]

    if kind == "decision":
        chosen = {int(v) for v in form.getlist("answer")}
        ok = chosen == set(stage["correct"])
        return (1.0 if ok else 0.0), ok, stage["explain"]

    if kind == "terminal":
        answer = norm(form.get("answer", ""))
        ok = any(norm(phrase) in answer for phrase in stage["accept"])
        return (1.0 if ok else 0.0), ok, stage["explain"]

    if kind == "report":
        points = 0.0
        if form.get("severity") == stage["severity"]:
            points += 0.5
        remediation = form.get("remediation")
        if remediation is not None and str(remediation) == str(stage["remediation"]):
            points += 0.5
        return points, points == 1.0, stage["explain"]

    return 0.0, False, "Unknown stage type."


def mission_score(stages, points, wrong, hints, difficulty, minutes, elapsed):
    accuracy = points / max(1, len(stages))
    penalty = hints * 6 + wrong * 4
    time_bonus = 10 if elapsed <= minutes * 60 else 0
    score = max(0, min(100, round(accuracy * 100 - penalty + time_bonus)))
    xp = int(score * (1 + 0.25 * difficulty)) + 10
    return {
        "score": score,
        "xp": xp,
        "accuracy": round(accuracy * 100),
        "penalty": penalty,
        "time_bonus": time_bonus,
    }
