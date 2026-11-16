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


# Question formats: single-answer and multi-answer families. The original
# "analyze" and "decision" types remain fully supported.
SINGLE_TYPES = {"analyze", "true_false", "log_analysis", "command_output",
                "event_investigation", "scenario"}
MULTI_TYPES = {"decision", "incident_response", "evidence_id"}


def evaluate(stage, form):
    """Return (points 0..1, correct, explanation)."""
    kind = stage.get("type", "")

    if kind in SINGLE_TYPES:
        if kind == "true_false":
            answer = str(form.get("answer", "")).strip().lower()
            ok = answer == str(stage.get("correct", "")).strip().lower()
        else:
            answer = form.get("answer")
            ok = answer is not None and str(answer) == str(stage.get("correct"))
        return (1.0 if ok else 0.0), ok, stage.get("explain", "")

    if kind in MULTI_TYPES:
        chosen = {int(v) for v in form.getlist("answer")}
        ok = chosen == set(stage.get("correct", []))
        return (1.0 if ok else 0.0), ok, stage.get("explain", "")

    if kind == "terminal":
        answer = norm(form.get("answer", ""))
        ok = any(norm(phrase) in answer for phrase in stage.get("accept", []))
        return (1.0 if ok else 0.0), ok, stage.get("explain", "")

    if kind == "report":
        points = 0.0
        if form.get("severity") == stage.get("severity"):
            points += 0.5
        remediation = form.get("remediation")
        if remediation is not None and str(remediation) == str(stage.get("remediation")):
            points += 0.5
        return points, points == 1.0, stage.get("explain", "")

    return 0.0, False, "Unknown stage type."


def mission_score(stages, points, wrong, hints, difficulty, minutes, elapsed):
    accuracy = points / max(1, len(stages))
    penalty = hints * 6 + wrong * 4
    time_bonus = 10 if elapsed <= minutes * 60 else 0
    score = max(0, min(100, round(accuracy * 100 - penalty + time_bonus)))
    xp = xp_for(score, difficulty)
    return {
        "score": score,
        "xp": xp,
        "accuracy": round(accuracy * 100),
        "penalty": penalty,
        "time_bonus": time_bonus,
    }


def xp_for(score, difficulty):
    """XP for a given score at a given difficulty (0..3)."""
    return int(score * (1 + 0.25 * difficulty)) + 10


# Skill taxonomy per track, used by the analytics and review systems.
SKILLS = {
    "red": [
        "Reconnaissance", "Web Security", "API Security",
        "Vulnerability Identification", "Authentication Testing",
        "Security Reporting",
    ],
    "blue": [
        "Log Analysis", "Threat Detection", "Alert Triage",
        "Incident Response", "Threat Hunting", "Digital Forensics",
    ],
    "purple": [
        "Attack Understanding", "Detection Validation",
        "Incident Correlation", "Mitigation Planning",
    ],
}

# Fallback mapping from a mission category to a primary skill, used until a
# stage explicitly declares its own "skill".
CATEGORY_SKILL = {
    "Reconnaissance": "Reconnaissance",
    "Web Application": "Web Security",
    "API Security": "API Security",
    "Phishing Analysis": "Threat Detection",
    "SIEM Investigation": "Log Analysis",
    "Malware Analysis": "Digital Forensics",
    "Red vs SOC": "Incident Correlation",
}


def skill_for(mission, stage):
    if stage.get("skill"):
        return stage["skill"]
    return CATEGORY_SKILL.get(mission.get("category", ""), "General")
