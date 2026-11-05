"""Score blinded transcripts against ground truth and emit results.csv.

Scoring rule (plan: Procedure step 3): a flag is a true positive if it names
the correct line (+/- LINE_TOLERANCE) AND correctly characterizes the defect.

Only the first half of that is mechanical. This scorer therefore computes
line-proximity automatically and writes a 'characterization_verdict' column
that is left EMPTY for every line-matching flag, to be filled in by a human
or a separate annotator model that never sees the condition label.

ADJUDICATION RULE (fix this before adjudicating, not case-by-case after):
  'correct' - the flag names the seeded defect, in substance. Different
              wording or vocabulary is fine.
  'wrong'   - the flag lands on the right line but describes a DIFFERENT
              problem than the seeded one ("right line, wrong reason"), or
              is too vague to tell ("this looks suspicious").
A flag on an unrelated line is a false positive and is never adjudicated.

Metrics are computed twice:
  - '*_linematch'  : treats any line-matching flag as a TP (upper bound)
  - '*_adjudicated': honours characterization_verdict; requires adjudication

Until adjudication is done, the adjudicated columns are blank, not guessed.

Usage:
    python3 harness/score.py                      # emit flags for adjudication
    python3 harness/score.py --adjudicated adj.csv  # fold verdicts back in
"""

import argparse
import csv
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(ROOT, "results")
BLINDED = os.path.join(RESULTS_DIR, "blinded.jsonl")
KEY = os.path.join(RESULTS_DIR, "blinding_key.json")
GROUND_TRUTH = os.path.join(ROOT, "corpus", "ground_truth.json")
FLAGS_CSV = os.path.join(RESULTS_DIR, "flags_for_adjudication.csv")
RESULTS_CSV = os.path.join(RESULTS_DIR, "results.csv")

# Plan rev. 2 sec. 8.1: +/-1 is the primary criterion. On a 25-40 line file a
# +/-2 window spans a sixth of the file. +/-2 remains available as a
# pre-registered sensitivity analysis via --tolerance.
LINE_TOLERANCE = 1


def load_ground_truth():
    with open(GROUND_TRUTH) as fh:
        gt = json.load(fh)
    by_file = {}
    for rec in gt["seeded_bugs"]:
        by_file[rec["buggy_file"]] = rec
    return by_file


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adjudicated",
                    help="CSV of adjudicated flags to fold back in")
    ap.add_argument("--tolerance", type=int, default=LINE_TOLERANCE,
                    help="line-match tolerance; %d is the pre-registered "
                         "primary, 2 the sensitivity analysis"
                         % LINE_TOLERANCE)
    args = ap.parse_args()
    tolerance = args.tolerance

    for path in (BLINDED, KEY):
        if not os.path.exists(path):
            sys.stderr.write("missing %s - run harness/blind.py first\n" % path)
            return 2

    gt_by_file = load_ground_truth()
    with open(KEY) as fh:
        key = json.load(fh)

    blinded = []
    with open(BLINDED) as fh:
        for line in fh:
            line = line.strip()
            if line:
                blinded.append(json.loads(line))

    verdicts = {}
    if args.adjudicated:
        with open(args.adjudicated) as fh:
            for row in csv.DictReader(fh):
                verdicts[(row["instance_id"], int(row["flag_line"]))] = (
                    row["characterization_verdict"].strip().lower())

    flag_rows = []
    result_rows = []

    truncated = []

    for rec in blinded:
        meta = key[rec["instance_id"]]
        truth = gt_by_file.get(rec["file"])
        is_buggy = rec["variant"] == "buggy"
        bug_line = truth["bug_line"] if (is_buggy and truth) else None

        # Plan rev. 2 sec. 7.3: treatments emit their report LAST, after the
        # === REPORT === marker, so a response cut off at the token limit
        # loses precisely the scoreable part and would otherwise be recorded
        # as a clean miss. That artifact acts only on the verbose conditions,
        # so it must be excluded and counted, never scored as a false
        # negative.
        if meta.get("truncated") or meta.get("stop_reason") in (
                "max_tokens", "length"):
            truncated.append((rec["instance_id"], rec["file"],
                              meta["condition"]))
            continue

        line_match_positions = []
        tp_adj = 0
        adjudication_pending = False

        for pos, flag in enumerate(rec["flags"], 1):
            near = (bug_line is not None
                    and abs(flag["line"] - bug_line) <= tolerance)
            verdict = verdicts.get((rec["instance_id"], flag["line"]), "")

            if near:
                line_match_positions.append(pos)
                if verdict == "correct":
                    tp_adj += 1
                elif verdict == "":
                    adjudication_pending = True
                # Emit only line-matching flags for adjudication; a flag on an
                # unrelated line is a false positive regardless of wording.
                flag_rows.append({
                    "instance_id": rec["instance_id"],
                    "file": rec["file"],
                    "flag_line": flag["line"],
                    "flag_position": pos,
                    "ground_truth_line": bug_line,
                    "flag_description": flag["description"],
                    "ground_truth_description": truth["description"],
                    "characterization_verdict": verdict,
                })

        n_flags = len(rec["flags"])
        tp_lm = 1 if line_match_positions else 0
        fp_lm = n_flags - tp_lm

        row = {
            "instance_id": rec["instance_id"],
            "file": rec["file"],
            "variant": rec["variant"],
            "bug_class": rec["bug_class"],
            "domain": meta.get("domain", ""),
            "condition": meta["condition"],
            "model": meta["model"],
            "sample": meta.get("sample", 0),
            "total_flags": n_flags,
            "explicit_no_bugs": rec["explicit_no_bugs"],
            "input_tokens": meta["input_tokens"],
            "output_tokens": meta["output_tokens"],
            "true_positive_linematch": tp_lm if is_buggy else "",
            "false_positives_linematch": fp_lm if is_buggy else n_flags,
            "first_flag_position": (
                line_match_positions[0] if line_match_positions else ""),
        }

        if is_buggy:
            if adjudication_pending:
                row["true_positive_adjudicated"] = ""
                row["false_positives_adjudicated"] = ""
            else:
                row["true_positive_adjudicated"] = 1 if tp_adj else 0
                row["false_positives_adjudicated"] = n_flags - tp_adj
        else:
            # Every flag on a bug-free file is spurious by construction.
            row["true_positive_adjudicated"] = ""
            row["false_positives_adjudicated"] = n_flags

        result_rows.append(row)

    result_rows.sort(key=lambda r: (r["condition"], r["bug_class"],
                                    r["file"], r["sample"]))

    if flag_rows:
        with open(FLAGS_CSV, "w", newline="") as fh:
            w = csv.DictWriter(
                fh, fieldnames=list(flag_rows[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(flag_rows)

    with open(RESULTS_CSV, "w", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=list(result_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(result_rows)

    pending = sum(1 for r in result_rows
                  if r["variant"] == "buggy"
                  and r["true_positive_adjudicated"] == "")
    print("scored %d instance(s) at tolerance +/-%d -> %s"
          % (len(result_rows), tolerance, RESULTS_CSV))
    print("%d line-matching flag(s) -> %s" % (len(flag_rows), FLAGS_CSV))

    if truncated:
        print("\nWARNING: %d instance(s) hit the token limit and were "
              "EXCLUDED, not scored as misses:" % len(truncated))
        for iid, fname, cond in truncated[:10]:
            print("  %s  %-40s %s" % (iid, fname, cond))
        if len(truncated) > 10:
            print("  ... and %d more" % (len(truncated) - 10))
        print("Raise MAX_TOKENS in run_pilot.py and re-run those instances. "
              "Truncation strikes the verbose conditions only, so leaving "
              "these in would bias against the treatments.")
    if pending:
        print("\n%d buggy instance(s) await characterization adjudication."
              % pending)
        print("Fill the 'characterization_verdict' column in %s with "
              "'correct' or 'wrong' for each row, then re-run:"
              % os.path.basename(FLAGS_CSV))
        print("  python3 harness/score.py --adjudicated %s" % FLAGS_CSV)
        print("Adjudicate WITHOUT consulting results/blinding_key.json.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
