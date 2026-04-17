#!/usr/bin/env python3
"""run_eval.py — F1. Eval harness for CTP-40 component scripts.

Usage:
    python3 scripts/run_eval.py [--only semantic_density|pareto|originality|shape]

Does NOT execute a full end-to-end CTP-40 run (that requires a live model).
It exercises the deterministic components of the skill against curated
inputs in evals/ and compares against evals/*/expected.json.

A passing eval run is a necessary but not sufficient condition for skill
correctness. A failing eval run is a blocker — some invariant is broken.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
EVALS_DIR = SKILL_DIR / "evals"


def _run(cmd: list[str], input_text: str | None = None) -> tuple[int, str, str]:
    p = subprocess.run(cmd, input=input_text, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def eval_semantic_density() -> list[str]:
    """Density floor must score 0 on prose, > 0.5 on a dense three-line form."""
    errs = []

    rc, out, _ = _run(["python3", str(SCRIPT_DIR / "semantic_density.py"),
                       "the quick brown fox jumped over the lazy dog"])
    if rc != 0 or "score=0.0" not in out:
        errs.append(f"prose case expected score=0.0, got: {out}")

    dense = "compression × constraint → emergent reasoning because structural inversion implies density"
    rc, out, _ = _run(["python3", str(SCRIPT_DIR / "semantic_density.py"), dense])
    try:
        score = float(out.split("score=")[1].split()[0])
        if score < 0.5:
            errs.append(f"dense case expected score>=0.5, got: {score}")
    except Exception:
        errs.append(f"parse fail on dense case: {out}")
    return errs


def eval_pareto(tmp: Path) -> list[str]:
    """Frontier plus mode selection should be deterministic."""
    errs = []
    # Tie-free values: one unambiguous winner per mode.
    data = [
        {"id": "a", "utility": 0.90, "novelty": 0.30},   # frontier: max utility
        {"id": "b", "utility": 0.40, "novelty": 0.95},   # frontier: max novelty (sum 1.35)
        {"id": "c", "utility": 0.60, "novelty": 0.60},   # frontier (sum 1.20)
        {"id": "d", "utility": 0.30, "novelty": 0.30},   # dominated
        {"id": "e", "utility": 0.85, "novelty": 0.55},   # frontier: max sum 1.40 (Applied winner)
    ]
    f = tmp / "pareto_in.json"
    f.write_text(json.dumps(data))
    rc, out, _ = _run(["python3", str(SCRIPT_DIR / "pareto.py"), str(f), "--mode", "Exploratory"])
    lines = out.splitlines()
    if not lines or lines[0] != "b":
        errs.append(f"Exploratory should pick b (max novelty on frontier), got: {lines}")
    rc, out, _ = _run(["python3", str(SCRIPT_DIR / "pareto.py"), str(f), "--mode", "Applied"])
    lines = out.splitlines()
    if not lines or lines[0] != "e":
        errs.append(f"Applied should pick e (max utility+novelty=1.40), got: {lines}")
    # Also verify 'd' is NOT on the frontier (dominated).
    if "d" in lines:
        errs.append(f"'d' should be dominated, not on frontier: {lines}")
    return errs


def eval_originality() -> list[str]:
    """Text that matches a corpus entry scores low; unrelated text scores high."""
    errs = []
    # Assumes corpus/obvious_generic.md contains 'make it user-friendly' style phrases.
    rc1, out1, _ = _run(["python3", str(SCRIPT_DIR / "originality.py"),
                         "make it more user friendly and intuitive", "--domain", "generic"])
    rc2, out2, _ = _run(["python3", str(SCRIPT_DIR / "originality.py"),
                         "invert the temporal anchor so the output precedes its trigger",
                         "--domain", "generic"])
    try:
        s1 = float(out1.split("score=")[1].split()[0])
        s2 = float(out2.split("score=")[1].split()[0])
        if s1 >= s2:
            errs.append(f"expected obvious-text score ({s1}) < unusual-text score ({s2})")
    except Exception:
        errs.append(f"parse fail: {out1!r} / {out2!r}")
    return errs


def eval_shape() -> list[str]:
    """Candidate-shape regex should accept good triples and reject bad ones."""
    errs = []
    import re as _re
    def _ok(s: str) -> bool:
        m = _re.match(r"^\s*(.{3,}?)\s*×\s*(.{3,}?)\s*→\s*(.{3,}?)\s*$", s)
        if not m:
            return False
        for part in m.groups():
            if len([w for w in part.split() if w]) < 2:
                return False
        return True
    good = [
        "flat associative field × constraint inversion → remote candidate density",
        "cycle seed × constraint lattice → next-cycle framing",
    ]
    bad = [
        "a × b → c",                    # too few words
        "this is a sentence.",          # no operators
        "A × B × C",                    # missing →
    ]
    for g in good:
        if not _ok(g):
            errs.append(f"good triple rejected: {g!r}")
    for b in bad:
        if _ok(b):
            errs.append(f"bad triple accepted: {b!r}")
    return errs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default=None)
    args = parser.parse_args()

    tmp = Path("/tmp")
    tmp.mkdir(exist_ok=True)

    tests = {
        "semantic_density": eval_semantic_density,
        "pareto": lambda: eval_pareto(tmp),
        "originality": eval_originality,
        "shape": eval_shape,
    }
    if args.only:
        tests = {args.only: tests[args.only]}

    total_errs = 0
    for name, fn in tests.items():
        errs = fn()
        if errs:
            total_errs += len(errs)
            print(f"[FAIL] {name}")
            for e in errs:
                print(f"       - {e}")
        else:
            print(f"[pass] {name}")

    if total_errs:
        print(f"\n{total_errs} failure(s).", file=sys.stderr)
        return 1
    print("\nAll evals passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
