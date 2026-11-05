"""Blinding manipulation check (plan rev. 2 sec. 10).

Reducing a transcript to its FLAG lines removes the overlay reasoning, and
blind.py additionally scrubs condition-revealing vocabulary from the flag
descriptions. Neither step is self-evidently sufficient, and a blinding
procedure that is assumed to work rather than measured is not a blinding
procedure.

This asks an independent model to name the condition that produced each
blinded flag set. If it does better than chance by a meaningful margin, the
blinding failed and the writeup must report it as failed rather than claim
the adjudication was blind.

The model sees only what the adjudicator sees. It never sees blinding_key.json.

Usage:
    export ANTHROPIC_API_KEY=...      # or DEEPSEEK_API_KEY
    python3 harness/guess_condition.py --model claude-sonnet-5
    python3 harness/guess_condition.py --model deepseek-chat
    python3 harness/guess_condition.py --offline   # lexical leak scan only
"""

import argparse
import collections
import json
import math
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provider

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
BLINDED = os.path.join(RESULTS_DIR, "blinded.jsonl")
KEY = os.path.join(RESULTS_DIR, "blinding_key.json")
OUT = os.path.join(RESULTS_DIR, "manipulation_check.json")

# Vocabulary that should NOT survive blinding. If any of this reaches the
# adjudicator, the scrub in blind.py has a gap.
LEAK_TERMS = [
    "duck", "lion", "river", "lantern", "bestiary", "creature", "beast",
    "sort_a", "sort_b", "sort_c", "ill-sorted", "ill sorted", "well-sorted",
    "lattice", "ontology", "overlay", "narrative", "story", "fable",
]


def load_blinded():
    with open(BLINDED) as fh:
        return [json.loads(line) for line in fh if line.strip()]


def render(rec):
    if not rec["flags"]:
        return "NO BUGS FOUND" if rec["explicit_no_bugs"] else "(no output)"
    return "\n".join("FLAG line=%d :: %s" % (f["line"], f["description"])
                     for f in rec["flags"])


def offline_leak_scan(blinded, key):
    """Count surviving giveaway terms, per condition. No API calls."""
    hits = collections.defaultdict(collections.Counter)
    for rec in blinded:
        cond = key[rec["instance_id"]]["condition"]
        text = render(rec).lower()
        for term in LEAK_TERMS:
            n = len(re.findall(r"\b%s\b" % re.escape(term), text))
            if n:
                hits[cond][term] += n
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--provider", choices=["anthropic", "deepseek", "openai"],
                    help="override provider autodetection from --model")
    ap.add_argument("--offline", action="store_true",
                    help="lexical leak scan only; make no API calls")
    ap.add_argument("--limit", type=int, default=60,
                    help="how many instances to ask about")
    ap.add_argument("--seed", type=int, default=20260827)
    args = ap.parse_args()

    for path in (BLINDED, KEY):
        if not os.path.exists(path):
            sys.stderr.write("missing %s - run harness/blind.py first\n" % path)
            return 2

    blinded = load_blinded()
    with open(KEY) as fh:
        key = json.load(fh)

    conditions = sorted(set(v["condition"] for v in key.values()))
    chance = 1.0 / len(conditions)

    print("conditions present: %s" % ", ".join(conditions))
    print("chance accuracy: %.3f\n" % chance)

    leaks = offline_leak_scan(blinded, key)
    print("--- lexical leak scan (terms that survived blinding) ---")
    if not leaks:
        print("  none: no giveaway vocabulary survived the scrub\n")
    else:
        for cond in sorted(leaks):
            terms = ", ".join("%s x%d" % (t, n)
                              for t, n in leaks[cond].most_common())
            print("  %-22s %s" % (cond, terms))
        print("  ^ any hit here is a gap in blind.py's SCRUB_PATTERNS\n")

    if args.offline:
        json.dump({"leak_scan": {k: dict(v) for k, v in leaks.items()},
                   "guessing": "skipped (--offline)"},
                  open(OUT, "w"), indent=2)
        print("wrote %s" % OUT)
        return 0

    try:
        client = provider.Client(args.model, args.provider)
    except RuntimeError as exc:
        sys.stderr.write("%s\n" % exc)
        return 2
    sample = list(blinded)
    random.Random(args.seed).shuffle(sample)
    sample = sample[:args.limit]

    described = {
        "control": "a plain review with no reasoning shown",
        "control_plus": "a careful step-by-step review, no relabeling",
        "treatment_a": "a fictional-creature overlay",
        "treatment_a_scrambled": "a randomly-assigned creature overlay",
        "treatment_b": "an abstract sort/type-lattice overlay",
        "treatment_c": "a real domain-semantics labeling",
    }
    menu = "\n".join("- %s: %s" % (c, described.get(c, c))
                     for c in conditions)

    correct = 0
    per_cond = collections.Counter()
    per_cond_total = collections.Counter()
    records = []

    for i, rec in enumerate(sample, 1):
        truth = key[rec["instance_id"]]["condition"]
        prompt = (
            "Below are the bug-report flags produced by one of several code "
            "review procedures. The reasoning has been stripped and "
            "vocabulary scrubbed.\n\nWhich procedure produced them?\n\n%s\n\n"
            "Answer with exactly one identifier from the list, nothing "
            "else.\n\n---\n%s\n---" % (menu, render(rec)))
        try:
            resp = client.complete(prompt, max_tokens=32, temperature=0.0)
            guess = resp.text.strip()
        except Exception as exc:
            sys.stderr.write("guess failed: %s\n" % exc)
            continue

        guess = next((c for c in conditions if c in guess), guess)
        per_cond_total[truth] += 1
        if guess == truth:
            correct += 1
            per_cond[truth] += 1
        records.append({"instance_id": rec["instance_id"],
                        "truth": truth, "guess": guess})
        if i % 20 == 0:
            print("  ...%d/%d" % (i, len(sample)))

    n = len(records)
    acc = correct / n if n else 0.0
    # Binomial tail: P(at least this many correct | guessing at chance).
    p = sum(math.comb(n, k) * chance ** k * (1 - chance) ** (n - k)
            for k in range(correct, n + 1)) if n else 1.0

    print("\n--- condition-guessing result ---")
    print("  n=%d  correct=%d  accuracy=%.3f  chance=%.3f  p=%.4g"
          % (n, correct, acc, chance, p))
    for cond in sorted(per_cond_total):
        print("    %-22s %d/%d" % (cond, per_cond[cond], per_cond_total[cond]))

    failed = p < 0.05 and acc > chance
    print("\n  VERDICT: blinding %s"
          % ("FAILED - report adjudication as non-blind"
             if failed else "held at this sample size"))

    json.dump({"leak_scan": {k: dict(v) for k, v in leaks.items()},
               "n": n, "correct": correct, "accuracy": acc,
               "chance": chance, "p_value": p, "blinding_failed": failed,
               "guesses": records}, open(OUT, "w"), indent=2)
    print("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
