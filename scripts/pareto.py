#!/usr/bin/env python3
"""pareto.py — D3. Compute the Pareto frontier over (x, y) points and
select by mode.

Usage:
    python3 scripts/pareto.py <candidates.json> [--mode MODE]

Input JSON shape:
    [
      {"id": "c1", "utility": 0.52, "novelty": 0.80, "x_extra": ...},
      ...
    ]

Output (stdout): newline-separated frontier IDs; the first line is the
selected ID under the given mode.

Mode selection rule:
    Exploratory   -> max novelty on frontier
    Applied       -> max (utility + novelty) on frontier
    Combinatorial -> max novelty on frontier with utility >= 0.5, else max sum
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def pareto_frontier(points: list[dict]) -> list[dict]:
    """Return the subset of points that are not dominated by any other."""
    frontier = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if (
                q["utility"] >= p["utility"]
                and q["novelty"] >= p["novelty"]
                and (q["utility"] > p["utility"] or q["novelty"] > p["novelty"])
            ):
                dominated = True
                break
        if not dominated:
            frontier.append(p)
    return frontier


def select(frontier: list[dict], mode: str) -> dict:
    if not frontier:
        raise ValueError("empty frontier")
    if mode == "Exploratory":
        return max(frontier, key=lambda p: p["novelty"])
    if mode == "Applied":
        return max(frontier, key=lambda p: p["utility"] + p["novelty"])
    if mode == "Combinatorial":
        eligible = [p for p in frontier if p["utility"] >= 0.5]
        pool = eligible if eligible else frontier
        return max(pool, key=lambda p: p["novelty"] if eligible else p["utility"] + p["novelty"])
    raise ValueError(f"unknown mode {mode!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidates_json")
    parser.add_argument("--mode", default="Exploratory")
    args = parser.parse_args()

    pts = json.loads(Path(args.candidates_json).read_text())
    for p in pts:
        for k in ("id", "utility", "novelty"):
            if k not in p:
                print(f"candidate missing '{k}': {p}", file=sys.stderr)
                return 2

    frontier = pareto_frontier(pts)
    chosen = select(frontier, args.mode)
    print(chosen["id"])
    for p in frontier:
        if p is not chosen:
            print(p["id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
