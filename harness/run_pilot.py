"""Execute the pilot grid: every (file, condition) pair as an independent
API call with no conversation carryover.

Writes one JSON record per instance to results/transcripts.jsonl, containing
the exact prompt sent, the verbatim response, and token counts. Raw output is
never summarized or discarded (plan: Execution Notes).

The run is resumable: instances already present in transcripts.jsonl are
skipped, so an interrupted run can be restarted without re-billing.

Usage:
    export ANTHROPIC_API_KEY=...      # or DEEPSEEK_API_KEY / OPENAI_API_KEY
    python3 harness/run_pilot.py --model claude-sonnet-5
    python3 harness/run_pilot.py --model deepseek-chat
    python3 harness/run_pilot.py --model claude-sonnet-5 --conditions control,treatment_a
    python3 harness/run_pilot.py --dry-run        # print the grid, call nothing
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provider

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT_DIR = os.path.join(ROOT, "prompts")
RESULTS_DIR = os.path.join(ROOT, "results")
TRANSCRIPTS = os.path.join(RESULTS_DIR, "transcripts.jsonl")

CONDITIONS = {
    "control": "control.txt",
    "control_plus": "control_plus.txt",
    "treatment_a": "treatment_a_narrative.txt",
    "treatment_a_scrambled": "treatment_a_scrambled.txt",
    "treatment_b": "treatment_b_typed.txt",
    "treatment_c": "treatment_c_domain.txt",
}

# Plan rev. 2 sec. 7.3: the treatments put their report last, so truncation
# destroys exactly the scoreable part. Headroom here is cheap; a truncated
# instance is an excluded instance.
MAX_TOKENS = 8192

# Plan rev. 2 sec. 7.2: k >= 3 samples at temperature 1.0. The variance across
# samples -- which ontology the model happens to draw -- is the term revision 1
# could not observe at all, and the practical question depends on it.
TEMPERATURE = 1.0

# Stop a doomed run early rather than repeating one auth/model error 360 times.
CONSECUTIVE_FAILURE_LIMIT = 5


def number_lines(source):
    """Prepend 1-indexed line numbers so FLAG line=N is scoreable.

    Applied identically under every condition, so it cannot advantage one.
    """
    lines = source.split("\n")
    width = len(str(len(lines)))
    return "\n".join("%*d | %s" % (width, i + 1, line)
                     for i, line in enumerate(lines))


def load_instances(ground_truth_path):
    with open(ground_truth_path) as fh:
        gt = json.load(fh)

    instances = []
    for rec in gt["seeded_bugs"]:
        instances.append({
            "file": rec["buggy_file"],
            "variant": "buggy",
            "bug_class": rec["bug_class"],
            "domain": rec["domain"],
        })
        # Matched bug-free twin, for the false-positive baseline.
        instances.append({
            "file": rec["correct_file"],
            "variant": "correct",
            "bug_class": rec["bug_class"],
            "domain": rec["domain"],
        })
    return instances


def instance_key(rec):
    return "%s|%s|%s|%s" % (rec["file"], rec["condition"], rec["model"],
                            rec.get("sample", 0))


def load_completed(path):
    done = set()
    if not os.path.exists(path):
        return done
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(instance_key(json.loads(line)))
            except (ValueError, KeyError):
                continue
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-5")
    ap.add_argument("--provider", choices=["anthropic", "deepseek", "openai"],
                    help="override provider autodetection from --model")
    ap.add_argument("--conditions",
                    default="control,control_plus,treatment_a,treatment_c",
                    help="comma-separated; rev. 2 pilot is "
                         "control,control_plus,treatment_a,treatment_c")
    ap.add_argument("--samples", type=int, default=3,
                    help="samples per (file, condition); plan rev. 2 "
                         "requires k >= 3")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds to pause between calls")
    args = ap.parse_args()

    if args.samples < 3:
        sys.stderr.write(
            "WARNING: k=%d. Plan rev. 2 sec. 7.2 requires k >= 3; below that "
            "the between-sample variance is unobtainable.\n" % args.samples)

    conditions = [c.strip() for c in args.conditions.split(",") if c.strip()]
    unknown = [c for c in conditions if c not in CONDITIONS]
    if unknown:
        sys.stderr.write("unknown condition(s): %s\n" % ", ".join(unknown))
        return 2

    templates = {}
    for cond in conditions:
        with open(os.path.join(PROMPT_DIR, CONDITIONS[cond])) as fh:
            templates[cond] = fh.read()

    instances = load_instances(os.path.join(ROOT, "corpus", "ground_truth.json"))
    grid = [(inst, cond, s)
            for inst in instances
            for cond in conditions
            for s in range(args.samples)]

    print("grid: %d instances x %d conditions x %d samples = %d calls "
          "(model=%s, temp=%.1f)"
          % (len(instances), len(conditions), args.samples, len(grid),
             args.model, TEMPERATURE))

    if args.dry_run:
        for inst, cond, s in grid[:10]:
            print("  %-40s %-22s %-8s sample=%d"
                  % (inst["file"], cond, inst["variant"], s))
        if len(grid) > 10:
            print("  ... and %d more" % (len(grid) - 10))
        return 0

    try:
        client = provider.Client(args.model, args.provider)
    except RuntimeError as exc:
        sys.stderr.write("%s\n" % exc)
        return 2

    os.makedirs(RESULTS_DIR, exist_ok=True)
    completed = load_completed(TRANSCRIPTS)
    if completed:
        print("resuming: %d instance(s) already recorded, will skip"
              % len(completed))

    print("provider: %s" % client.provider)
    written = 0
    failed = 0

    truncated = 0

    with open(TRANSCRIPTS, "a") as out:
        for i, (inst, cond, sample) in enumerate(grid, 1):
            key = "%s|%s|%s|%s" % (inst["file"], cond, args.model, sample)
            if key in completed:
                continue

            with open(os.path.join(ROOT, inst["file"])) as fh:
                source = fh.read()
            prompt = templates[cond].replace("{code}", number_lines(source))

            # Fresh single-turn request: no history is ever carried between
            # instances, so an overlay built for one file cannot leak forward.
            try:
                resp = client.complete(prompt, MAX_TOKENS, TEMPERATURE)
            except Exception as exc:
                failed += 1
                sys.stderr.write("[%d/%d] FAILED %s %s: %s\n"
                                 % (i, len(grid), inst["file"], cond, exc))
                # Abort a run that is failing from the first call: an auth
                # error or a bad model name fails identically 360 times, and
                # grinding through the whole grid to say so wastes the
                # operator's time and can still bill for partial attempts.
                if failed >= CONSECUTIVE_FAILURE_LIMIT and written == 0:
                    sys.stderr.write(
                        "\nAborting: the first %d call(s) all failed and "
                        "nothing succeeded. Check the API key, the model "
                        "name, and network access, then re-run -- completed "
                        "work is resumable.\n"
                        % CONSECUTIVE_FAILURE_LIMIT)
                    return 2
                continue

            record = dict(inst)
            record.update({
                "condition": cond,
                "model": args.model,
                "sample": sample,
                "temperature": TEMPERATURE,
                "prompt": prompt,
                "response": resp.text,
                "provider": client.provider,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "stop_reason": resp.stop_reason,
                "truncated": resp.truncated,
                "timestamp": time.time(),
            })
            out.write(json.dumps(record) + "\n")
            out.flush()
            written += 1

            trunc = resp.truncated
            if trunc:
                truncated += 1
            print("[%d/%d] %s %s s=%d (in=%d out=%d)%s"
                  % (i, len(grid), inst["file"], cond, sample,
                     resp.input_tokens, resp.output_tokens,
                     "  *** TRUNCATED ***" if trunc else ""))

            if args.sleep:
                time.sleep(args.sleep)

    print("wrote %d new transcript(s) to %s" % (written, TRANSCRIPTS))
    if truncated:
        print("WARNING: %d response(s) hit the %d-token limit. score.py will "
              "EXCLUDE these rather than score them as misses, but they are "
              "lost data and bias against the verbose conditions. Raise "
              "MAX_TOKENS and re-run them." % (truncated, MAX_TOKENS))
    if failed:
        print("%d call(s) failed; re-run to retry just those" % failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
