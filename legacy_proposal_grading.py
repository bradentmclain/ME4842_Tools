"""Read-only cohort grading for the deployed legacy presentation rubric.

Legacy criteria and rating scale are retained. Corrected allocation: 20 individual
plus 15 group points. The faculty cohort is 75% and the student cohort is 25%.
"""

from collections import defaultdict
from math import fsum, isfinite

GROUP_FIELDS = (
    "technical_content_score",
    "experimental_efficacy_score",
    "completeness_score",
    "presentation_quality_score",
    "answering_questions_score",
)
INDIVIDUAL_FIELDS = (
    "dress_code_score",
    "audience_engagement_score",
    "body_language_score",
    "enthusiasm_score",
    "overall_score",
)
RATINGS = {"Substandard": 2, "Poor": 2.75, "Acceptable": 3.5, "Good": 4.25, "Excellent": 5}


def roster_roles(roster):
    roles = {}
    for entry in roster["students"]:
        name = entry.split(",")[-2].strip()
        roles[name] = "student"
    for entry in roster["instructors"]:
        roles[entry.split(",", 1)[0].strip()] = "faculty"
    return roles


def push_time(key):
    alphabet = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"
    if len(key) != 20 or any(c not in alphabet for c in key):
        raise ValueError("Expected Firebase push ID for legacy revision ordering.")
    result = 0
    for char in key[:8]:
        result = result * 64 + alphabet.index(char)
    return result


def grade_legacy(records, roles):
    """records: reviewer, firebase_key, response, optional source_url.

    Deduplicate by reviewer and target across both sources. Unknown roles or
    malformed scores stop grading; a missing cohort holds the component.
    """
    latest = {}
    for record in records:
        reviewer, row = record["reviewer"], record["response"]
        if reviewer not in roles or roles[reviewer] not in ("student", "faculty"):
            raise ValueError(f"Unreconciled reviewer: {reviewer}")
        kind = row.get("response_type")
        if kind not in ("Group", "Individual"):
            raise ValueError("Unknown response type.")
        target = (
            row.get("group_being_scored") if kind == "Group" else row.get("student_being_reviewed")
        )
        if not isinstance(target, str) or not target:
            raise ValueError("Missing evaluation target.")
        key = (reviewer, kind, target)
        stamp = row.get("submitted_at_ms", push_time(record["firebase_key"]))
        rank = (stamp, record["firebase_key"], record.get("source_url", ""))
        if key not in latest or rank > latest[key][0]:
            latest[key] = (rank, record)
    buckets = defaultdict(list)
    memberships = {}
    for (_, kind, target), (_, record) in latest.items():
        row = record["response"]
        buckets[(kind, target)].append(record)
        if kind == "Group":
            members = row.get("student_being_reviewed")
            if not isinstance(members, list) or not members:
                raise ValueError("Group members missing.")
            for member in members:
                if member in memberships and memberships[member] != target:
                    raise ValueError(f"Ambiguous group membership: {member}")
                memberships[member] = target
    result = {
        "policy": "legacy-cohort-75-25-20i-15g-v2",
        "latest_records": len(latest),
        "groups": {},
        "individuals": {},
    }
    for (kind, target), rows in sorted(buckets.items()):
        fields = GROUP_FIELDS if kind == "Group" else INDIVIDUAL_FIELDS
        criteria, holds = {}, []
        for field in fields:
            cohorts = {"student": [], "faculty": []}
            for record in rows:
                value = record["response"].get(field)
                if kind == "Individual":
                    if value not in RATINGS:
                        raise ValueError(f"Invalid individual rating: {target}/{field}")
                    value = RATINGS[value] * 20
                else:
                    if (
                        isinstance(value, bool)
                        or not isinstance(value, (int, float))
                        or not isfinite(value)
                        or not 0 <= value <= 10
                    ):
                        raise ValueError(f"Invalid group score: {target}/{field}")
                    value *= 10
                cohorts[roles[record["reviewer"]]].append(value)
            detail = {
                role: {"count": len(values), "mean": fsum(values) / len(values) if values else None}
                for role, values in cohorts.items()
            }
            missing = [role for role, values in cohorts.items() if not values]
            holds.extend(missing)
            detail["percent"] = (
                None
                if missing
                else 0.75 * detail["faculty"]["mean"] + 0.25 * detail["student"]["mean"]
            )
            criteria[field] = detail
        component = {
            "percent": None
            if holds
            else fsum(c["percent"] for c in criteria.values()) / len(fields),
            "missing_cohorts": sorted(set(holds)),
            "criteria": criteria,
            "feedback": [
                {"reviewer": r["reviewer"], "text": r["response"].get("written_feedback", "")}
                for r in rows
                if r["response"].get("written_feedback")
            ],
        }
        result["groups" if kind == "Group" else "individuals"][target] = component
    result["memberships"] = memberships
    result["point_allocation"] = {"individual": 20, "group": 15, "total": 35}
    result["students"] = {}
    for student, group in sorted(memberships.items()):
        individual = result["individuals"].get(student)
        team = result["groups"][group]
        held = individual is None or individual["percent"] is None or team["percent"] is None
        ind_points = (
            None
            if individual is None or individual["percent"] is None
            else individual["percent"] * 20 / 100
        )
        group_points = None if team["percent"] is None else team["percent"] * 15 / 100
        result["students"][student] = {
            "group": group,
            "individual_points": ind_points,
            "group_points": group_points,
            "total_points": None if held else ind_points + group_points,
            "held": held,
        }
    return result
