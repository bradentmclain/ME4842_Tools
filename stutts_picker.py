#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ranked-Preference Two-Elective Scheduler (Heat Transfer = Week 1)
=================================================================
Author: Dr. Daniel S. Stutts
Date Created: 2025-08-21
Last Updated: 2025-08-21
 - Adds Week 1 Heat Transfer on the main Schedule sheet (lists all groups)
 - Adds Roster + Week1_HeatTransfer sheets
 - Adds Capacities sheet (per-week capacity/assigned/remaining)
 - Stricter input parsing (no phantom/duplicate groups)
 - Clearer Notes (per-week capacity = 1; across two weeks ≤ 2 per elective)
 - Tie-break jitter with --seed; UNLISTED_PENALTY explanation

Overview
--------
Schedules TWO electives per group across TWO elective weeks (Weeks 2 & 3),
with Heat Transfer fixed to Week 1 for all groups.

Inputs (Excel, default sheet "Input")
------------------------------------
Columns: Group, Size (ignored), and the five electives:
  - Acoustics
  - Dynamic Balancing
  - Piezoelectric Beam
  - Pump Characterization
  - Tuned Mass Damper
Each group must rank 4 or 5 electives using integers starting at 1
(1 = best, no duplicates per row). Unranked electives (if ranking only 4)
are allowed and will be assigned UNLISTED_PENALTY cost if used.

Capacity & Feasibility
----------------------
- Per-week capacity: ONE group per elective per lab meeting (per week).
- We schedule EXACTLY two elective weeks (Weeks 2 & 3), so each elective
  can host up to TWO groups total across those weeks (one in Week 2 and one in Week 3).
- With 5 electives × 1 station per week, at most 5 groups in the section.

Cost model
----------
- If elective e is ranked r (1..5) by group g, cost = r - 1  (1→0, 2→1, ...).
- If e is unranked (only 4 ranked), cost = UNLISTED_PENALTY (default 5).
- A tiny random jitter (~1e-4) is added to costs to break ties fairly.
  Use --seed for reproducibility (any integer, 42 is just a convention).

Outputs (Excel)
---------------
- Schedule: Week 1 shows Heat Transfer (all groups). Weeks 2 & 3 show assignments.
- ByGroup: for each group, assigned electives, weeks (2/3), ranks, and costs.
- Summary: total cost.
- Costs: full cost matrix (group × elective).
- Roster: the exact groups used.
- Week1_HeatTransfer: explicit per-group listing for Week 1.
- Capacities: per-week capacity/assigned/remaining for all experiments.

CLI
---
python3 scheduler_ranked_preferences.py \
  --input FS_ranked_prefs_input.xlsx \
  --output schedule_out.xlsx \
  --seed 42 \
  --unlisted-penalty 5
"""

from __future__ import annotations
import argparse
import sys
import json
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd

# Electives to schedule in Weeks 2 & 3 (Heat Transfer is fixed to Week 1)
ELECTIVES: List[str] = ['Acoustics', 'Pump', 'Tuned Mass Damper', 'Dynamic Balancing', 'Piezoelectric']


# ---------------------------------------------------------------------------
# Input parsing and cost matrix construction
# ---------------------------------------------------------------------------

def process_input_and_build_costs(
    input_data: List[Dict[str, Any]],
    electives: List[str],
    unlisted_penalty: int,
    seed: int | None
) -> Tuple[List[str], Dict[str, Dict[str, float]], Dict[str, Dict[str, int | None]]]:
    """
    Build:
      - groups: list[str]
      - costs: dict[group][elective] -> float
      - ranks: dict[group][elective] -> int|None (None if unranked)

    Rules:
      - Each entry must have a non-empty unique Group value.
      - Each group must rank 4 or 5 electives, using 1..5 with no duplicates.
      - Cost = (rank-1) if ranked; else UNLISTED_PENALTY.
      - A tiny random jitter is added to each (g,e) cost to break ties.
    """
    rng = np.random.default_rng(seed)
    groups: List[str] = []
    ranks: Dict[str, Dict[str, int | None]] = {}
    costs: Dict[str, Dict[str, float]] = {}

    seen = set()
    for entry in input_data:
        g_raw = entry.get("Group", None)
        if g_raw is None:
            continue
        g = str(g_raw).strip()
        if not g or g.lower() == "nan":
            continue
        if g in seen:
            raise ValueError(f'Duplicate group name detected: "{g}". Group names must be unique.')

        # Collect ranks (based on the order of electives in the list)
        rank_vals: Dict[str, int] = {}
        ranked_electives = entry.get("Electives", [])

        if not 4 <= len(ranked_electives) <= 5:
            raise ValueError(f'Group "{g}" must rank between 4 and 5 electives (ranked {len(ranked_electives)}).')

        # Assign ranks based on their position in the list (favorite first, least favorite last)
        for idx, elective in enumerate(ranked_electives):
            # Dirty hack.
            if elective not in electives:
                raise ValueError(f'Invalid elective "{elective}" for group "{g}".')
            rank_vals[elective] = idx + 1  # Rank starts from 1

        seen.add(g)
        groups.append(g)
        ranks[g] = {e: rank_vals.get(e, None) for e in electives}

        # Build cost row with jitter
        costs[g] = {}
        for e in electives:
            base = (rank_vals.get(e, None) - 1) if e in rank_vals else float(unlisted_penalty)
            jitter = rng.uniform(0, 1e-4)  # tiny, only for tie-breaking
            costs[g][e] = base + jitter

    return groups, costs, ranks


def read_input_and_build_costs(path: str, sheet: str, unlisted_penalty: int, seed: int | None
                               ) -> Tuple[List[str], Dict[str, Dict[str, float]], Dict[str, Dict[str, int | None]]]:
    """
    Read the Excel input and build:
      - groups: list[str]
      - costs: dict[group][elective] -> float
      - ranks: dict[group][elective] -> int|None (None if unranked)

    Rules:
      - Each kept row must have a non-empty unique Group value.
      - Each group must rank 4 or 5 electives, using 1..5 with no duplicates.
      - Cost = (rank-1) if ranked; else UNLISTED_PENALTY.
      - A tiny random jitter is added to each (g,e) cost to break ties.
    """
    df = pd.read_excel(path, sheet_name=sheet, dtype=object)

    if "Group" not in df.columns:
        raise ValueError('Input must contain a "Group" column.')

    missing = [e for e in ELECTIVES if e not in df.columns]
    if missing:
        raise ValueError(f"Missing elective column(s): {missing}. Expected columns: {ELECTIVES}")

    rng = np.random.default_rng(seed)
    groups: List[str] = []
    ranks: Dict[str, Dict[str, int | None]] = {}
    costs: Dict[str, Dict[str, float]] = {}

    seen = set()
    for _, row in df.iterrows():
        g_raw = row.get("Group", None)
        if pd.isna(g_raw):
            continue
        g = str(g_raw).strip()
        if not g or g.lower() == "nan":
            continue
        if g in seen:
            raise ValueError(f'Duplicate group name detected: "{g}". Group names must be unique.')

        # Collect ranks
        rank_vals: Dict[str, int] = {}
        for e in ELECTIVES:
            v = row[e]
            if pd.isna(v):
                continue
            try:
                r = int(v)
            except Exception:
                raise ValueError(f'Non-integer rank for group "{g}", elective "{e}": {v!r}')
            if not (1 <= r <= 5):
                raise ValueError(f'Ranks must be within 1..5. Found {r} for "{g}" / "{e}"')
            if r in rank_vals.values():
                raise ValueError(f'Duplicate rank {r} for group "{g}". Use each rank once.')
            rank_vals[e] = r

        if len(rank_vals) < 4 or len(rank_vals) > 5:
            raise ValueError(f'Group "{g}" must rank 4 or 5 electives (ranked {len(rank_vals)}).')

        seen.add(g)
        groups.append(g)
        ranks[g] = {e: rank_vals.get(e, None) for e in ELECTIVES}

        # Build cost row with jitter
        costs[g] = {}
        for e in ELECTIVES:
            base = (rank_vals[e] - 1) if e in rank_vals else float(unlisted_penalty)
            jitter = rng.uniform(0, 1e-4)  # tiny, only for tie-breaking
            costs[g][e] = base + jitter

    return groups, costs, ranks



# ---------------------------------------------------------------------------
# ILP (optimal) and Greedy solvers
# ---------------------------------------------------------------------------
def solve_ilp(groups: List[str], costs: Dict[str, Dict[str, float]], T: int = 2):
    """
    Integer Linear Program with variables x[g,t,e] in {0,1}:
      - Minimize sum_{g,t,e} x[g,t,e] * costs[g][e]
      Subject to:
        (1) For each group g and week t in {1,2}: sum_e x[g,t,e] = 1
        (2) For each group g and elective e:      sum_t x[g,t,e] <= 1  (no repeats)
        (3) For each week t and elective e:       sum_g x[g,t,e] <= 1  (one station per week)
    """
    try:
        import pulp
    except ImportError:
        return None, "pulp_not_available"

    prob = pulp.LpProblem("RankedPreferencesTwoElectiveScheduling", pulp.LpMinimize)

    x = pulp.LpVariable.dicts(
        "x",
        ((g, t, e) for g in groups for t in range(1, T + 1) for e in ELECTIVES),
        lowBound=0, upBound=1, cat=pulp.LpBinary
    )

    # Objective
    prob += pulp.lpSum(x[g, t, e] * costs[g][e] for g in groups for t in range(1, T + 1) for e in ELECTIVES)

    # (1) One elective per group per week
    for g in groups:
        for t in range(1, T + 1):
            prob += pulp.lpSum(x[g, t, e] for e in ELECTIVES) == 1

    # (2) No repeating an elective for the same group
    for g in groups:
        for e in ELECTIVES:
            prob += pulp.lpSum(x[g, t, e] for t in range(1, T + 1)) <= 1

    # (3) One station per elective per week
    for t in range(1, T + 1):
        for e in ELECTIVES:
            prob += pulp.lpSum(x[g, t, e] for g in groups) <= 1

    status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
    try:
        from pulp import LpStatus
        status_str = LpStatus[status]
    except Exception:
        status_str = str(status)

    if status_str != "Optimal":
        return None, f"not_optimal:{status_str}"

    # Extract
    schedule = {t: {e: None for e in ELECTIVES} for t in range(1, T + 1)}
    by_group = {g: {} for g in groups}
    total_cost = 0.0
    group_cost = {g: 0.0 for g in groups}

    for g in groups:
        for t in range(1, T + 1):
            for e in ELECTIVES:
                if x[g, t, e].value() > 0.5:
                    schedule[t][e] = g
                    by_group[g][e] = t
                    total_cost += costs[g][e]
                    group_cost[g] += costs[g][e]

    return {"schedule": schedule, "by_group": by_group, "total_cost": total_cost, "group_cost": group_cost}, "ok"


def solve_greedy(groups: List[str], costs: Dict[str, Dict[str, float]], T: int = 2):
    """
    Greedy fallback:
      For each week, repeatedly assign the (group, elective) pair with minimal cost
      among unassigned groups and unused electives, ensuring no group repeats an elective.
    """
    schedule = {t: {e: None for e in ELECTIVES} for t in range(1, T + 1)}
    by_group = {g: {} for g in groups}
    assigned = {g: set() for g in groups}

    for t in range(1, T + 1):
        remaining_electives = set(ELECTIVES)
        remaining_groups = set(groups)

        while remaining_electives and remaining_groups:
            best = None
            best_val = float("inf")
            for e in list(remaining_electives):
                for g in list(remaining_groups):
                    if e in assigned[g]:
                        continue
                    val = costs[g][e]
                    if val < best_val:
                        best_val = val
                        best = (g, e)
            if best is None:
                break

            g, e = best
            schedule[t][e] = g
            by_group[g][e] = t
            assigned[g].add(e)
            remaining_electives.remove(e)
            remaining_groups.remove(g)

    # Sanity check: each group must have T electives assigned
    print(assigned)
    
    for g in groups:
        if len(assigned[g]) == T:
            print(f"Assigned to group {g}")
        else:
            raise RuntimeError(f"Greedy failed to assign two electives for group {g}.")

    total_cost = 0.0
    group_cost = {}
    for g in groups:
        c = sum(costs[g][e] for e in assigned[g])
        group_cost[g] = c
        total_cost += c

    return {"schedule": schedule, "by_group": by_group, "total_cost": total_cost, "group_cost": group_cost}, "ok_greedy"


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------
def write_output(output_path: str,
                 result: Dict[str, Any],
                 groups: List[str],
                 costs: Dict[str, Dict[str, float]],
                 ranks: Dict[str, Dict[str, int | None]],
                 seed: int | None,
                 unlisted_penalty: int,
                 T: int = 2) -> None:
    """
    Create the Excel workbook with sheets:
      - Schedule (Week 1 Heat Transfer + Weeks 2/3 electives)
      - ByGroup
      - Summary
      - Costs
      - Roster
      - Week1_HeatTransfer
      - Capacities
      - Notes
    """
    # Helper for readability in Excel
    def tidy(x):
        return "" if x is None else x

    # 1) Schedule sheet with Week 1 visible and Heat Transfer column
    rows = []
    # Week 1 row: list all groups in Heat Transfer cell (wrapped)
    ht_list = "\n".join(groups)
    row_w1 = {"Week": 1, "Heat Transfer": ht_list}
    for e in ELECTIVES:
        row_w1[e] = ""
    rows.append(row_w1)

    # Weeks 2 & 3 rows
    for t in range(1, T + 1):
        row = {"Week": t + 1, "Heat Transfer": ""}
        for e in ELECTIVES:
            row[e] = tidy(result["schedule"][t][e])
        rows.append(row)
    df_sched = pd.DataFrame(rows, columns=["Week", "Heat Transfer", *ELECTIVES])

    # 2) ByGroup sheet
    rows_g = []
    for g in groups:
        row = {"Group": g, "Cost": round(result["group_cost"].get(g, float("nan")), 4)}
        for e in ELECTIVES:
            if e in result["by_group"][g]:
                # convert solver week index 1/2 -> calendar weeks 2/3
                row[f"{e} (week)"] = result["by_group"][g][e] + 1
                r = ranks[g][e]
                row[f"{e} (rank)"] = r if r is not None else f"unlisted({unlisted_penalty})"
                row[f"{e} (cost)"] = round(costs[g][e], 4)
        rows_g.append(row)
    df_bygroup = pd.DataFrame(rows_g)

    # 3) Summary
    df_summary = pd.DataFrame([{"Total Cost": round(result["total_cost"], 4)}])

    # 4) Cost matrix
    df_costs = pd.DataFrame.from_dict(costs, orient="index")[ELECTIVES].reset_index().rename(columns={"index": "Group"})

    # 5) Roster and Week 1 explicit listing
    df_roster = pd.DataFrame({"Group": groups})
    df_week1 = pd.DataFrame({"Group": groups, "Week": [1] * len(groups), "Experiment": ["Heat Transfer"] * len(groups)})

    # 6) Capacities (per-week capacity, assigned, remaining)
    cap_rows = []
    # Week 1
    cap_rows.append({"Week": 1, "Experiment": "Heat Transfer", "Capacity": len(groups), "Assigned": len(groups), "Remaining": 0})
    for e in ELECTIVES:
        cap_rows.append({"Week": 1, "Experiment": e, "Capacity": 0, "Assigned": 0, "Remaining": 0})
    # Weeks 2 & 3 (one station per elective per week)
    for t in range(1, T + 1):
        week = t + 1
        for e in ELECTIVES:
            assigned = 1 if (result["schedule"][t][e] is not None and result["schedule"][t][e] != "") else 0
            cap_rows.append({"Week": week, "Experiment": e, "Capacity": 1, "Assigned": assigned, "Remaining": 1 - assigned})
        cap_rows.append({"Week": week, "Experiment": "Heat Transfer", "Capacity": 0, "Assigned": 0, "Remaining": 0})
    df_caps = pd.DataFrame(cap_rows, columns=["Week", "Experiment", "Capacity", "Assigned", "Remaining"])

    # Write workbook
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        # Schedule
        df_sched.to_excel(writer, sheet_name="Schedule", index=False)
        ws = writer.sheets["Schedule"]
        wrap = writer.book.add_format({"text_wrap": True})
        ws.set_column(1, 1, 40, wrap)  # Heat Transfer column wide & wrapped

        # Other sheets
        df_bygroup.to_excel(writer, sheet_name="ByGroup", index=False)
        df_summary.to_excel(writer, sheet_name="Summary", index=False)
        df_costs.to_excel(writer, sheet_name="Costs", index=False)
        df_roster.to_excel(writer, sheet_name="Roster", index=False)
        df_week1.to_excel(writer, sheet_name="Week1_HeatTransfer", index=False)
        df_caps.to_excel(writer, sheet_name="Capacities", index=False)

        # Notes
        notes = writer.book.add_worksheet("Notes")
        notes.write(0, 0, "Notes:")
        notes.write(1, 0, "- All groups perform Heat Transfer in Week 1 (see Schedule and Week1_HeatTransfer).")
        notes.write(2, 0, "- Weeks 2 & 3 schedule the two electives with one station per elective per week.")
        notes.write(3, 0, "- Capacity: per week, at most 1 group per elective; with two elective weeks total, an elective can host up to 2 groups (one in Week 2 and one in Week 3).")
        notes.write(4, 0, f"- UNLISTED_PENALTY = {unlisted_penalty} (used if a group did not rank an elective; higher = avoid unlisted more strongly).")
        notes.write(5, 0, f"- Seed = {seed if seed is not None else '(none)'} (controls tie-break reproducibility).")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Ranked-preference two-elective scheduler (Heat Transfer fixed to Week 1).")
    parser.add_argument("--input", required=True, help="Path to input Excel file")
    parser.add_argument("--output", required=True, help="Path to output Excel file")
    parser.add_argument("--sheet", default="Input", help="Sheet name containing the table (default: Input)")
    parser.add_argument("--solver", choices=["pulp", "greedy"], default="pulp", help="Use PuLP+CBC if available, else greedy")
    parser.add_argument("--unlisted-penalty", type=int, default=5, help="Penalty if an elective was not ranked (default: 5)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for tie-break jitter (default: None)")
    args = parser.parse_args()

    groups, costs, ranks = read_input_and_build_costs(args.input, args.sheet, args.unlisted_penalty, args.seed)

    if len(groups) > 5:
        raise SystemExit(f"Infeasible: {len(groups)} groups but only 5 one-station electives per week. Split the section or add capacity.")

    if args.solver == "pulp":
        result, status = solve_ilp(groups, costs, T=2)
        if status != "ok":
            print(f"Falling back to greedy due to ILP status: {status}", file=sys.stderr)
            result, status = solve_greedy(groups, costs, T=2)
    else:
        result, status = solve_greedy(groups, costs, T=2)

    write_output(args.output, result, groups, costs, ranks, args.seed, args.unlisted_penalty, T=2)
    print(json.dumps({"status": status, "total_cost": result["total_cost"], "groups": len(groups)}))


if __name__ == "__main__":
    main()
