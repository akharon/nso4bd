"""Compute precision/recall/F1/FP-rate/cost per condition and run the
paired significance tests described in the plan.

Primary pre-registered outcome: overall F1, control vs. each treatment.
Secondary/exploratory: per-bug-class breakdowns, Holm-Bonferroni corrected.

Uses an exact two-sided McNemar test (binomial on the discordant pairs), so
no SciPy dependency is required and small discordant counts stay valid.

Usage:  python3 harness/analyze.py [--metric linematch|adjudicated]
"""

import argparse
import collections
import csv
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_CSV = os.path.join(ROOT, "results", "results.csv")


def exact_mcnemar(b, c):
    """Two-sided exact McNemar on discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2.0 ** n)
    return min(1.0, 2.0 * tail)


def holm_bonferroni(pvals):
    """Return Holm-adjusted p-values, order preserved."""
    indexed = sorted(enumerate(pvals), key=lambda t: t[1])
    m = len(pvals)
    adjusted = [0.0] * m
    running = 0.0
    for rank, (idx, p) in enumerate(indexed):
        val = (m - rank) * p
        running = max(running, val)
        adjusted[idx] = min(1.0, running)
    return adjusted


def f1(precision, recall):
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def summarize(rows, tp_col, fp_col):
    """Precision/recall/F1 over buggy rows; FP-rate over correct rows."""
    buggy = [r for r in rows if r["variant"] == "buggy"]
    correct = [r for r in rows if r["variant"] == "correct"]

    usable = [r for r in buggy if r[tp_col] != ""]
    if not usable:
        return None

    tp = sum(int(r[tp_col]) for r in usable)
    fp = sum(int(r[fp_col]) for r in usable if r[fp_col] != "")
    n_bugs = len(usable)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / n_bugs if n_bugs else 0.0

    clean_flags = sum(int(r["total_flags"]) for r in correct)
    clean_files_flagged = sum(1 for r in correct if int(r["total_flags"]) > 0)

    all_rows = usable + correct
    tokens_in = sum(int(r["input_tokens"]) for r in all_rows)
    tokens_out = sum(int(r["output_tokens"]) for r in all_rows)

    positions = [int(r["first_flag_position"]) for r in usable
                 if r["first_flag_position"] != ""]

    return {
        "n_buggy": n_bugs,
        "n_correct": len(correct),
        "tp": tp,
        "fp": fp,
        "precision": precision,
        "recall": recall,
        "f1": f1(precision, recall),
        "fp_rate_clean_files": (
            clean_files_flagged / len(correct) if correct else 0.0),
        "spurious_flags_per_clean_file": (
            clean_flags / len(correct) if correct else 0.0),
        "mean_tokens_per_review": (
            (tokens_in + tokens_out) / len(all_rows) if all_rows else 0.0),
        "mean_first_flag_position": (
            sum(positions) / len(positions) if positions else float("nan")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metric", choices=["linematch", "adjudicated"],
                    default="linematch")
    ap.add_argument("--rule", choices=["majority", "best", "unanimous"],
                    default="majority",
                    help="how to collapse the k samples per file; "
                         "majority is the pre-registered primary")
    args = ap.parse_args()

    if not os.path.exists(RESULTS_CSV):
        sys.stderr.write("missing %s - run harness/score.py first\n"
                         % RESULTS_CSV)
        return 2

    tp_col = "true_positive_%s" % args.metric
    fp_col = "false_positives_%s" % args.metric

    with open(RESULTS_CSV) as fh:
        rows = list(csv.DictReader(fh))

    if not rows:
        sys.stderr.write("results.csv is empty - nothing to analyze\n")
        return 2

    print("metric basis: %s" % args.metric)
    if args.metric == "linematch":
        print("NOTE: line-match treats any flag landing within the scoring "
              "tolerance of the seeded bug as a true positive, without "
              "checking that the defect was described correctly. It is an "
              "UPPER BOUND on true performance. Adjudicate and re-run with "
              "--metric adjudicated for the plan's actual criterion.")
    print()

    models = sorted(set(r["model"] for r in rows))
    for model in models:
        model_rows = [r for r in rows if r["model"] == model]
        conditions = sorted(set(r["condition"] for r in model_rows))

        print("=" * 72)
        print("MODEL: %s" % model)
        print("=" * 72)

        header = ("%-14s %5s %5s %6s %6s %6s %8s %9s %8s"
                  % ("condition", "TP", "FP", "prec", "rec", "F1",
                     "FP/clean", "tok/rev", "firstpos"))
        print(header)
        print("-" * len(header))

        summaries = {}
        for cond in conditions:
            s = summarize([r for r in model_rows if r["condition"] == cond],
                          tp_col, fp_col)
            summaries[cond] = s
            if s is None:
                print("%-14s  (no adjudicated data yet)" % cond)
                continue
            print("%-14s %5d %5d %6.3f %6.3f %6.3f %8.3f %9.0f %8.2f"
                  % (cond, s["tp"], s["fp"], s["precision"], s["recall"],
                     s["f1"], s["spurious_flags_per_clean_file"],
                     s["mean_tokens_per_review"],
                     s["mean_first_flag_position"]))

        if any(s is None for s in summaries.values()):
            print("\nSignificance tests skipped: adjudication incomplete.")
            continue

        if not ({"control", "control_plus"} & set(conditions)):
            print("\nNo baseline condition present; skipping paired tests.")
            continue

        # --- Primary: paired per-file outcomes, control vs each treatment ---
        print("\nPaired McNemar (exact, two-sided) vs. baseline, per-file "
              "bug-detection outcome:")

        def outcomes(cond, rule=None):
            """Collapse the k samples of each file into one 0/1 outcome.

            Plan rev. 2 sec. 11 pre-registers majority-of-3 as the primary
            rule, with best-of-3 and unanimous-3 as sensitivity analyses.
            Treating each sample as an independent observation would inflate
            n threefold and violate McNemar's pairing assumption, so the
            samples are aggregated per file before testing.
            """
            rule = rule or args.rule
            per_file = {}
            for r in model_rows:
                if (r["condition"] == cond and r["variant"] == "buggy"
                        and r[tp_col] != ""):
                    per_file.setdefault(r["file"], []).append(int(r[tp_col]))
            out = {}
            for fname, hits in per_file.items():
                if rule == "best":
                    out[fname] = 1 if any(hits) else 0
                elif rule == "unanimous":
                    out[fname] = 1 if all(hits) else 0
                else:
                    out[fname] = 1 if sum(hits) * 2 > len(hits) else 0
            return out

        # Primary comparison is against control_plus when present: the plain
        # control forbids deliberation, so control-vs-treatment measures the
        # reasoning pass, not the overlay (plan rev. 2 sec. 5).
        baseline = "control_plus" if "control_plus" in conditions else "control"
        if baseline != "control_plus":
            print("\n  WARNING: control_plus absent. Comparing against the "
                  "plain control measures deliberation, not relabeling.")
        print("\n  baseline: %s   sample-aggregation rule: %s-of-k"
              % (baseline, args.rule))

        ctrl = outcomes(baseline)
        treatments = [c for c in conditions if c != baseline]
        pvals = []
        details = []
        for cond in treatments:
            treat = outcomes(cond)
            shared = sorted(set(ctrl) & set(treat))
            b = sum(1 for f in shared if ctrl[f] == 1 and treat[f] == 0)
            c = sum(1 for f in shared if ctrl[f] == 0 and treat[f] == 1)
            p = exact_mcnemar(b, c)
            pvals.append(p)
            details.append((cond, len(shared), b, c, p))

        adj = holm_bonferroni(pvals) if pvals else []
        print("  %-14s %6s %8s %8s %9s %9s"
              % ("treatment", "n", "ctrl+only", "trt+only", "p", "p_holm"))
        for (cond, n, b, c, p), pa in zip(details, adj):
            print("  %-14s %6d %8d %8d %9.4f %9.4f" % (cond, n, b, c, p, pa))

        if pvals:
            print("\n  'ctrl+only' = files only the baseline caught; "
                  "'trt+only' = files only the treatment caught.")
            print("  Holm correction applied across the %d treatment "
                  "comparisons." % len(pvals))

        # --- Between-sample variance (plan rev. 2 sec. 7.2/8) ---
        # The term revision 1 could not observe at all: does the overlay work
        # reliably, or only when the model happens to draw a lucky ontology?
        print("\nBetween-sample stability (k samples per file):")
        print("  %-22s %10s %10s %10s %12s"
              % ("condition", "major.", "best-of-k", "unanim.", "unstable"))
        for cond in conditions:
            maj = outcomes(cond, "majority")
            best = outcomes(cond, "best")
            unan = outcomes(cond, "unanimous")
            if not maj:
                continue
            n = len(maj)
            # Files where the samples disagreed: caught sometimes, missed
            # others. High values mean a single run is close to a coin flip.
            unstable = sum(1 for f in best if best[f] != unan.get(f, 0))
            print("  %-22s %10.3f %10.3f %10.3f %8d/%d"
                  % (cond, sum(maj.values()) / n, sum(best.values()) / n,
                     sum(unan.values()) / n, unstable, n))
        print("  'unstable' = files the condition caught on some samples and "
              "missed on others.")
        print("  A large best-vs-unanimous gap means the result depends on "
              "which ontology the model happened to draw.")

        # --- Secondary: per-bug-class, exploratory ---
        print("\nPer-bug-class F1 (secondary/exploratory):")
        classes = sorted(set(r["bug_class"] for r in model_rows))
        print("  %-20s %s" % ("bug_class",
                              " ".join("%12s" % c for c in conditions)))
        for bc in classes:
            cells = []
            for cond in conditions:
                s = summarize(
                    [r for r in model_rows
                     if r["condition"] == cond and r["bug_class"] == bc],
                    tp_col, fp_col)
                cells.append("%12.3f" % s["f1"] if s else "%12s" % "-")
            print("  %-20s %s" % (bc, " ".join(cells)))

        n_per_cell = len(set(r["file"] for r in model_rows
                             if r["variant"] == "buggy")) // max(
                                 len(classes), 1)
        print("\n  With ~%d file(s) per class, per-class cells are far too "
              "small for inference; read them as descriptive only."
              % n_per_cell)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
