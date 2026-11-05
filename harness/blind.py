"""Blind transcripts before scoring (plan: Procedure step 3).

Reduces each transcript to just its FLAG lines, discarding the Steps 1-3
reasoning. This removes both overlay vocabulary ("duck", "SORT_A") and the
structural giveaways ("=== REPORT ===", "Cast the characters") that would
otherwise reveal the condition to the scorer.

Emits results/blinded.jsonl with a shuffled, opaque instance_id. The mapping
back to condition lives in results/blinding_key.json, which the scorer must
not read.

Usage:  python3 harness/blind.py [--seed 12345]
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
TRANSCRIPTS = os.path.join(RESULTS_DIR, "transcripts.jsonl")
BLINDED = os.path.join(RESULTS_DIR, "blinded.jsonl")
KEY = os.path.join(RESULTS_DIR, "blinding_key.json")

FLAG_RE = re.compile(r"^\s*FLAG\s+line\s*=\s*(\d+)\s*::\s*(.*)$",
                     re.IGNORECASE)
NO_BUGS_RE = re.compile(r"^\s*NO BUGS FOUND\s*$", re.IGNORECASE)

# Plan rev. 2 sec. 10: reducing a transcript to its FLAG lines removes the
# overlay reasoning but NOT the flag descriptions, which can still name
# creatures or report an expression as ill-sorted. Without this scrub the
# adjudicator can often infer the condition from the description alone, which
# defeats the blinding. The manipulation check (guess_condition.py) measures
# whether what remains still leaks.
SCRUB_PATTERNS = [
    # Treatment B: opaque sort labels and ill-sortedness verdicts.
    (re.compile(r"\bSORT_[A-Z0-9_]+\b"), "the sort"),
    (re.compile(r"\bill[- ]sorted\b", re.IGNORECASE), "inconsistent"),
    (re.compile(r"\bwell[- ]sorted\b", re.IGNORECASE), "consistent"),
    (re.compile(r"\bsort lattice\b", re.IGNORECASE), "the scheme"),
    (re.compile(r"\boperation table\b", re.IGNORECASE), "the scheme"),
    (re.compile(r"\bsorts?\b", re.IGNORECASE), "kind"),
    # Treatment A: the bestiary. Creature nouns are the giveaway; the rest of
    # the sentence carries the actual claim about the defect.
    (re.compile(r"\b(ducks?|lions?|rivers?|lanterns?|foxes|fox|owls?|bears?|"
                r"wolves|wolf|serpents?|dragons?|falcons?|stags?|hares?|"
                r"beetles?|moths?|ravens?|otters?|badgers?|herons?|"
                r"bestiary|creatures?|beasts?)\b", re.IGNORECASE), "entity"),
    (re.compile(r"\b(eats?|eaten|eating|devours?|drinks?|drunk|carries|"
                r"carried|merges? with)\b", re.IGNORECASE), "combines with"),
    # Treatment C and generic: overlay-process vocabulary.
    (re.compile(r"\b(my|the) (ontology|overlay|bestiary|rule ?set)\b",
                re.IGNORECASE), "the scheme"),
    (re.compile(r"\bnarrative rule\b", re.IGNORECASE), "rule"),
]


def scrub(text):
    """Strip condition-revealing vocabulary from a flag description."""
    for pattern, replacement in SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def extract_flags(response):
    """Pull ordered FLAG entries out of a response.

    Only the report section is kept. If a '=== REPORT ===' marker is present,
    everything before it is discarded outright; otherwise every FLAG-shaped
    line in the text is taken, which is the control condition's normal shape.
    """
    text = response
    marker = text.rfind("=== REPORT ===")
    if marker != -1:
        text = text[marker + len("=== REPORT ==="):]

    flags = []
    explicit_none = False
    for line in text.split("\n"):
        m = FLAG_RE.match(line)
        if m:
            raw_desc = m.group(2).strip()
            flags.append({
                "line": int(m.group(1)),
                "description": scrub(raw_desc),
                "description_raw": raw_desc,
            })
        elif NO_BUGS_RE.match(line):
            explicit_none = True
    return flags, explicit_none


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260827)
    args = ap.parse_args()

    if not os.path.exists(TRANSCRIPTS):
        sys.stderr.write(
            "no transcripts at %s - run harness/run_pilot.py first\n"
            % TRANSCRIPTS)
        return 2

    records = []
    with open(TRANSCRIPTS) as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    blinded = []
    key = {}
    for rec in records:
        raw = "%s|%s|%s|%s" % (rec["file"], rec["condition"], rec["model"],
                               rec.get("sample", 0))
        instance_id = hashlib.sha256(
            ("%d:%s" % (args.seed, raw)).encode()).hexdigest()[:16]

        flags, explicit_none = extract_flags(rec["response"])
        blinded.append({
            "instance_id": instance_id,
            "file": rec["file"],
            "variant": rec["variant"],
            "bug_class": rec["bug_class"],
            "flags": flags,
            "explicit_no_bugs": explicit_none,
        })
        key[instance_id] = {
            "file": rec["file"],
            "condition": rec["condition"],
            "model": rec["model"],
            "variant": rec["variant"],
            "bug_class": rec["bug_class"],
            "domain": rec.get("domain", ""),
            "sample": rec.get("sample", 0),
            "input_tokens": rec["input_tokens"],
            "output_tokens": rec["output_tokens"],
            "stop_reason": rec.get("stop_reason", ""),
            "truncated": rec.get("truncated", False),
            "provider": rec.get("provider", ""),
        }

    random.Random(args.seed).shuffle(blinded)

    with open(BLINDED, "w") as fh:
        for rec in blinded:
            fh.write(json.dumps(rec) + "\n")
    with open(KEY, "w") as fh:
        json.dump(key, fh, indent=2)

    unparsed = sum(1 for b in blinded
                   if not b["flags"] and not b["explicit_no_bugs"])
    print("blinded %d transcript(s) -> %s" % (len(blinded), BLINDED))
    print("key -> %s (scorer must not read this)" % KEY)
    if unparsed:
        print("WARNING: %d response(s) yielded neither FLAG lines nor an "
              "explicit NO BUGS FOUND. Inspect these before trusting the "
              "metrics - the plan's pilot exists partly to catch exactly "
              "this parseability failure." % unparsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
