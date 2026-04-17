#!/usr/bin/env python3
"""originality.py — D1. Externally anchored originality score.

Usage:
    python3 scripts/originality.py <proposition_text> --domain <domain>

Score = 1 - max cosine-like overlap against every entry in the domain's
'obvious response' corpus file (corpus/obvious_<domain>.md). The corpus
files are short curated lists of the most common framings for that domain.
Structural distance from the nearest corpus entry is the anchor.

If no corpus for the domain exists, falls back to a domain-agnostic
corpus (corpus/obvious_generic.md) and prints a warning.

This is approximate; the goal is removing Claude's self-judgement, not
producing a perfect metric.
"""
from __future__ import annotations
import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
CORPUS_DIR = SCRIPT_DIR.parent / "corpus"


def _tokens(s: str) -> list[str]:
    s = re.sub(r"[^a-z0-9\s×→]+", " ", s.lower())
    return [t for t in s.split() if t and t not in {"a", "an", "the", "of", "to", "is", "are", "by", "for", "with", "and", "or"}]


def _bigrams(toks: list[str]) -> list[str]:
    return [f"{a} {b}" for a, b in zip(toks, toks[1:])]


def _vec(s: str) -> Counter:
    toks = _tokens(s)
    c = Counter(toks)
    c.update(_bigrams(toks))
    return c


def _cos(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a[k] * b[k] for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _load_corpus(domain: str) -> tuple[list[str], str]:
    path = CORPUS_DIR / f"obvious_{domain}.md"
    if not path.exists():
        fallback = CORPUS_DIR / "obvious_generic.md"
        if not fallback.exists():
            return [], "none"
        path = fallback
        src = "generic"
    else:
        src = domain
    entries = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        if line:
            entries.append(line)
    return entries, src


def originality(text: str, domain: str) -> dict:
    entries, src = _load_corpus(domain)
    if not entries:
        return {"score": 0.5, "nearest": None, "overlap": 0.0, "corpus": "none"}
    t_vec = _vec(text)
    best = 0.0
    best_entry = None
    for e in entries:
        sim = _cos(t_vec, _vec(e))
        if sim > best:
            best = sim
            best_entry = e
    return {
        "score": round(max(0.0, 1.0 - best), 4),
        "nearest": best_entry,
        "overlap": round(best, 4),
        "corpus": src,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("text")
    parser.add_argument("--domain", default="generic")
    args = parser.parse_args()
    r = originality(args.text, args.domain)
    print(f"score={r['score']} overlap={r['overlap']} corpus={r['corpus']}")
    if r["nearest"]:
        print(f"nearest={r['nearest']!r}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
