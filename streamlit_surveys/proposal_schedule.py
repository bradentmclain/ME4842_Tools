"""Approved Fall 2026 presentation exception; enrollment and group IDs stay intact."""

from copy import deepcopy

NOTICE = "Group 309D presents with Section 301 on Tuesday, October 13, 2026 at 9:00 AM Central."


def apply_presentation_schedule(groups, students):
    groups, students = deepcopy(groups), deepcopy(students)
    members = groups.get("309", {}).pop("309D", None)
    if members is not None:
        groups.setdefault("301", {})["309D"] = members
    for actor in students.values():
        if actor.get("group") == "309D" and actor.get("section") == "309":
            actor["registered_section"] = "309"
            actor["section"] = "301"
    return groups, students


def presentation_section(group):
    return "301" if group == "309D" else group[:3]
