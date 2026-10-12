from copy import deepcopy

import pytest

from legacy_proposal_grading import (
    GROUP_FIELDS,
    INDIVIDUAL_FIELDS,
    grade_legacy,
    roster_roles,
)


def row(reviewer, score, key, kind="Group", **extra):
    response = dict.fromkeys(GROUP_FIELDS if kind == "Group" else INDIVIDUAL_FIELDS, score)
    response.update(
        response_type=kind,
        group_being_scored="301A",
        student_being_reviewed=["Presenter"] if kind == "Group" else "Presenter",
        **extra,
    )
    return dict(reviewer=reviewer, firebase_key="--------" + key.zfill(12), response=response)


def test_cohort_sizes_do_not_change_split_and_data_unchanged():
    rows = [row(f"s{i}", 6, str(i)) for i in range(30)] + [
        row("ta1", 10, "90"),
        row("ta2", 10, "91"),
    ]
    original = deepcopy(rows)
    roles = {
        r["reviewer"]: "faculty" if r["reviewer"].startswith("ta") else "student" for r in rows
    }
    report = grade_legacy(rows, roles)
    assert report["groups"]["301A"]["percent"] == 90
    assert rows == original


def test_latest_cross_source_and_role_from_roster_not_payload():
    old = row("s", 10, "1", scoring_weight=3)
    new = row("s", 0, "2", submitted_at_ms=100, scoring_weight=3)
    new["source_url"] = "fall"
    report = grade_legacy([old, new, row("ta", 10, "3")], {"s": "student", "ta": "faculty"})
    assert report["latest_records"] == 2
    assert report["groups"]["301A"]["percent"] == 75


def test_individual_ratings_and_missing_cohort_hold():
    rows = [row("s", "Substandard", "1", "Individual"), row("ta", "Excellent", "2", "Individual")]
    assert (
        grade_legacy(rows, {"s": "student", "ta": "faculty"})["individuals"]["Presenter"]["percent"]
        == 85
    )
    comp = grade_legacy(rows[:1], {"s": "student"})["individuals"]["Presenter"]
    assert comp["percent"] is None
    assert comp["missing_cohorts"] == ["faculty"]


def test_invalid_scores_and_unknown_reviewers_fail():
    with pytest.raises(ValueError, match="Unreconciled"):
        grade_legacy([row("unknown", 5, "1")], {})
    for value in (None, True, -1, 11, float("nan")):
        with pytest.raises(ValueError, match="Invalid group"):
            grade_legacy([row("s", value, "1")], {"s": "student"})


def test_aliases_are_one_faculty_identity():
    roster = {
        "students": ["301,301A,Zachary Boeringa,zlbgkd@mst.edu"],
        "instructors": [
            "Zachary Boeringa, zlbgkd@mst.edu",
            "Zachary Boeringa, zlbgkd@umsystem.edu",
        ],
    }
    assert roster_roles(roster) == {"Zachary Boeringa": "faculty"}
