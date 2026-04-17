#!/usr/bin/env python3
"""semantic_density.py — D2. Deterministic semantic-density score for a
proposition (one line) or a three-line blend.

Usage:
    python3 scripts/semantic_density.py "<text>"
    echo "<text>" | python3 scripts/semantic_density.py -

Definition:
    density = operators_in_text / word_count
    normalized_score = min(1.0, density / 0.15)

Where operators are the set below. A pure-prose sentence with no operators
scores 0.0 and triggers the phase-4 hard floor.
"""
from __future__ import annotations
import re
import sys


# Structural reasoning operators. Tuned for the CTP-40 three-line form.
# Keep this list conservative; every addition here loosens the floor.
OPERATORS = {
    # symbolic
    "×", "→", "⇒", "⊢", "∴", "¬", "↔", "∧", "∨", "≥", "≤",
    # causal / implicational
    "because", "therefore", "hence", "thus", "implies", "produces",
    "yields", "entails", "results", "causes", "drives", "forces",
    # conditional / temporal
    "if", "when", "unless", "whenever", "after", "before", "while",
    # mapping / identity
    "maps", "is", "acts", "becomes", "inverts", "substitutes",
    # comparative
    "versus", "vs", "against",
}


def _tokenize(text: str) -> list[str]:
    # Preserve single-char symbolic operators as their own tokens.
    out = []
    buf = []
    for ch in text:
        if ch in "×→⇒⊢∴¬↔∧∨":
            if buf:
                out.append("".join(buf))
                buf = []
            out.append(ch)
        elif ch.isspace():
            if buf:
                out.append("".join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return [t.lower().strip(".,;:()\"'`[]{}") for t in out if t.strip()]


def density_of(text: str) -> tuple[float, float, int, int]:
    tokens = _tokenize(text)
    words = [t for t in tokens if t]
    if not words:
        return 0.0, 0.0, 0, 0
    ops = sum(1 for t in words if t in OPERATORS)
    raw = ops / len(words)
    score = min(1.0, raw / 0.15)
    return round(score, 4), round(raw, 4), ops, len(words)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: semantic_density.py <text> | -", file=sys.stderr)
        return 2
    text = sys.stdin.read() if sys.argv[1] == "-" else sys.argv[1]
    score, raw, ops, n = density_of(text)
    # Machine-readable single-line output.
    print(f"score={score} raw={raw} operators={ops} words={n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
