"""Generate the buggy corpus from the correct corpus by applying exactly one
documented mutation per file, and emit ground_truth.json.

Each mutation is an exact string substitution against the correct source. The
script fails loudly if a pattern does not match exactly once, so the corpus can
never drift silently out of sync with the ground truth.

Usage:  python3 harness/build_corpus.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import divergence

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORRECT_DIR = os.path.join(ROOT, "corpus", "correct")
BUGGY_DIR = os.path.join(ROOT, "corpus", "buggy")
GROUND_TRUTH = os.path.join(ROOT, "corpus", "ground_truth.json")

# (correct_filename, bug_class, domain, old, new, description)
#
# Plan rev. 2 sec. 6.2: bug class must be FULLY CROSSED with domain, one file
# per (class, domain) cell. Revision 1's corpus was not: the classes where H2
# predicts an effect were also the numeric/ID files and the classes where it
# predicts a null were mostly control-flow, so a class effect and a domain
# effect predicted identical data. Five files were re-authored into their
# missing domains to close that.
MUTATIONS = [
    # ---- swapped operands / arguments ----
    (
        "c07_geo_fence.py", "swapped_operands", "numeric_units",
        "    return distance_m <= fence[\"radius_m\"]",
        "    return fence[\"radius_m\"] <= distance_m",
        "Comparison operands swapped: the fence test now matches vehicles "
        "OUTSIDE the radius instead of inside.",
    ),
    (
        "c13_audit_transfer.py", "swapped_operands", "id_handling",
        "    post_entry(ledger, source_account_id, -amount_cents, memo)\n"
        "    post_entry(ledger, dest_account_id, amount_cents, memo)",
        "    post_entry(ledger, dest_account_id, -amount_cents, memo)\n"
        "    post_entry(ledger, source_account_id, amount_cents, memo)",
        "Source and destination account IDs are swapped in the ledger "
        "postings: money moves the wrong direction.",
    ),
    (
        "c01_lane_routing.py", "swapped_operands", "control_flow",
        "    moved = source_lane[\"queued\"][:count]\n"
        "    source_lane[\"queued\"] = source_lane[\"queued\"][count:]\n"
        "    target_lane[\"queued\"].extend(moved)",
        "    moved = target_lane[\"queued\"][:count]\n"
        "    target_lane[\"queued\"] = target_lane[\"queued\"][count:]\n"
        "    source_lane[\"queued\"].extend(moved)",
        "Source and target lanes are swapped in rebalance: parcels move from "
        "the overflow lane into the already-full lane, the wrong direction.",
    ),

    # ---- wrong variable used ----
    (
        "c12_temperature_control.py", "wrong_variable", "numeric_units",
        "        \"current_celsius\": round(current_celsius, 2),",
        "        \"current_celsius\": round(sensor_fahrenheit, 2),",
        "Reports the raw Fahrenheit sensor reading in a field declared as "
        "Celsius.",
    ),
    (
        "c02_order_refund.py", "wrong_variable", "id_handling",
        "        \"line_item_id\": line_item_id,",
        "        \"line_item_id\": order[\"id\"],",
        "Audit record writes the order ID into the line_item_id field.",
    ),
    (
        "c09_state_machine.py", "wrong_variable", "control_flow",
        "    if not can_transition(current, target):",
        "    if not can_transition(target, current):",
        "Transition legality is checked with current and target reversed, so "
        "the guard consults the wrong row of the transition table.",
    ),

    # ---- unit / type mismatch ----
    (
        "c04_rate_limiter.py", "unit_type_mismatch", "numeric_units",
        "        return deficit_tokens / self.refill_per_second",
        "        return deficit_tokens * self.refill_per_second",
        "Tokens are multiplied by a rate (tokens/second) instead of divided, "
        "yielding tokens^2/second where seconds are required.",
    ),
    (
        "c10_tenant_lookup.py", "unit_type_mismatch", "id_handling",
        "    org_id = org_for_tenant(tenant_id, tenants)\n"
        "    if org_id is None:\n"
        "        return []\n"
        "    return [tid for tid, rec in tenants.items()\n"
        "            if rec[\"org_id\"] == org_id and tid != tenant_id]",
        "    org_id = org_for_tenant(tenant_id, tenants)\n"
        "    if org_id is None:\n"
        "        return []\n"
        "    return [tid for tid, rec in tenants.items()\n"
        "            if rec[\"org_id\"] == tenant_id and tid != tenant_id]",
        "Compares an org ID against a tenant ID: two different entity kinds "
        "held in the same shape, so the sibling list is always empty.",
    ),
    (
        "c15_batch_dispatch.py", "unit_type_mismatch", "control_flow",
        "        if payload_bytes > max_payload_bytes:",
        "        if len(batch) > max_payload_bytes:",
        "Compares an item COUNT against a BYTE budget.",
    ),

    # ---- off-by-one / control flow ----
    (
        "c03_sensor_window.py", "off_by_one", "numeric_units",
        "    for start in range(0, len(readings) - window_size + 1):",
        "    for start in range(0, len(readings) - window_size):",
        "Loop bound drops the final full window.",
    ),
    (
        "c11_member_roster.py", "off_by_one", "id_handling",
        "    start = (page_number - 1) * page_size",
        "    start = page_number * page_size",
        "Treats the 1-indexed page number as 0-indexed, skipping the first "
        "page of the member roster entirely.",
    ),
    (
        "c14_playlist_shuffle.py", "off_by_one", "control_flow",
        "    tail = ordered[-min_gap:] if min_gap > 0 else []",
        "    tail = ordered[-(min_gap - 1):] if min_gap > 0 else []",
        "Separation window is one track too short, so the artist-gap "
        "constraint is under-enforced.",
    ),

    # ---- missing null / bounds check ----
    (
        "c06_solar_yield.py", "missing_check", "numeric_units",
        "    if peak_sun_hours < 0:\n"
        "        return 0.0\n"
        "    clear_fraction = 1.0 - cloud_cover_fraction",
        "    clear_fraction = 1.0 - cloud_cover_fraction",
        "Removes the negative-irradiance guard, so a negative peak-sun-hours "
        "reading yields negative energy instead of zero.",
    ),
    (
        "c05_permission_grant.py", "missing_check", "id_handling",
        "    actor = membership_for(workspace, actor_user_id)\n"
        "    if actor is None:\n"
        "        return False\n"
        "    return rank_of(actor[\"role\"]) > rank_of(target_role)",
        "    actor = membership_for(workspace, actor_user_id)\n"
        "    return rank_of(actor[\"role\"]) > rank_of(target_role)",
        "Removes the None guard: a non-member actor raises TypeError instead "
        "of being denied.",
    ),
    (
        "c08_retry_backoff.py", "missing_check", "control_flow",
        "            if attempt == max_attempts - 1:\n"
        "                break\n",
        "",
        "Removes the final-attempt guard, so the loop sleeps after the last "
        "attempt before giving up.",
    ),
]

# Mutations deliberately excluded from the seeded set, with the reason.
# Kept in the record so any exclusion is auditable rather than invisible.
# (Empty now: the original c01 swap was behavior-preserving under abs() and
# was replaced with a genuine swap of the transit-time multipliers.)
EXCLUDED = set()


def line_of(text, needle):
    """1-indexed line number where needle begins."""
    return text[:text.index(needle)].count("\n") + 1


def main():
    os.makedirs(BUGGY_DIR, exist_ok=True)
    records = []
    excluded_records = []
    errors = []

    for fname, bug_class, domain, old, new, desc in MUTATIONS:
        src_path = os.path.join(CORRECT_DIR, fname)
        with open(src_path) as fh:
            source = fh.read()

        occurrences = source.count(old)
        if occurrences != 1:
            errors.append(
                "%s: pattern matched %d times (expected exactly 1)"
                % (fname, occurrences))
            continue

        record = {
            "correct_file": "corpus/correct/%s" % fname,
            "bug_class": bug_class,
            "domain": domain,
            "bug_line": line_of(source, old),
            "description": desc,
        }

        if fname in EXCLUDED:
            record["excluded_reason"] = (
                "Mutation is behavior-preserving; not a detectable defect.")
            excluded_records.append(record)
            continue

        buggy_name = "b" + fname[1:]
        mutated = source.replace(old, new)
        with open(os.path.join(BUGGY_DIR, buggy_name), "w") as fh:
            fh.write(mutated)

        record["buggy_file"] = "corpus/buggy/%s" % buggy_name
        record["bug_line"] = line_of(mutated, new) if new else record["bug_line"]

        # Plan rev. 2 sec. 6.3: prove the mutation actually changes behaviour.
        # A behaviour-preserving "defect" is undetectable in principle and
        # would depress recall equally across every condition.
        changed, detail = divergence.diverges(
            src_path, os.path.join(BUGGY_DIR, buggy_name))
        if not changed:
            errors.append(
                "%s: mutation appears BEHAVIOUR-PRESERVING (%s). A defect no "
                "input can reveal is undetectable in principle; exclude it or "
                "replace it." % (fname, detail))
            continue
        record["divergence_witness"] = detail

        records.append(record)

    # Plan rev. 2 sec. 6.2: class must be fully crossed with domain, or an
    # apparent H2 class effect is indistinguishable from a domain effect.
    cells = {}
    for r in records:
        cells.setdefault((r["bug_class"], r["domain"]), []).append(
            r["correct_file"])
    dupes = {k: v for k, v in cells.items() if len(v) > 1}
    classes = sorted(set(r["bug_class"] for r in records))
    domains = sorted(set(r["domain"] for r in records))
    missing = [(c, d) for c in classes for d in domains
               if (c, d) not in cells]
    if dupes or missing:
        for k, v in sorted(dupes.items()):
            errors.append("class/domain cell %s has %d files: %s"
                          % (k, len(v), ", ".join(v)))
        for k in missing:
            errors.append("class/domain cell %s is EMPTY" % (k,))

    if errors:
        for err in errors:
            sys.stderr.write("ERROR: %s\n" % err)
        return 1

    with open(GROUND_TRUTH, "w") as fh:
        json.dump({
            "seeded_bugs": records,
            "excluded_mutations": excluded_records,
        }, fh, indent=2)

    by_class = {}
    for r in records:
        by_class[r["bug_class"]] = by_class.get(r["bug_class"], 0) + 1
    print("wrote %d buggy files" % len(records))
    for k in sorted(by_class):
        print("  %-20s %d" % (k, by_class[k]))
    if excluded_records:
        print("excluded %d mutation(s):" % len(excluded_records))
        for r in excluded_records:
            print("  %s - %s" % (r["correct_file"], r["excluded_reason"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
