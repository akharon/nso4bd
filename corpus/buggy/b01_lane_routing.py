"""Routing parcels to sortation lanes."""

MAX_LANE_DEPTH = 40


def lane_for(parcel, lanes):
    """Pick the first lane whose destination matches the parcel's."""
    for lane in lanes:
        if lane["destination_hub"] == parcel["destination_hub"]:
            return lane
    return None


def is_overflowing(lane):
    return len(lane["queued"]) >= MAX_LANE_DEPTH


def assign(parcel, lanes, overflow_lane):
    lane = lane_for(parcel, lanes)
    if lane is None or is_overflowing(lane):
        overflow_lane["queued"].append(parcel["id"])
        return overflow_lane["id"]

    lane["queued"].append(parcel["id"])
    return lane["id"]


def rebalance(source_lane, target_lane, count):
    """Move `count` parcels from the fuller lane to the emptier one."""
    moved = target_lane["queued"][:count]
    target_lane["queued"] = target_lane["queued"][count:]
    source_lane["queued"].extend(moved)
    return len(moved)


def sweep(lanes, overflow_lane):
    reassigned = 0
    for lane in lanes:
        if is_overflowing(lane):
            reassigned += rebalance(lane, overflow_lane, 5)
    return reassigned
