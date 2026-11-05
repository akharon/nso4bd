"""Playlist ordering with artist-separation constraints."""


def group_by_artist(tracks):
    groups = {}
    for track in tracks:
        groups.setdefault(track["artist_id"], []).append(track)
    return groups


def violates_separation(ordered, candidate, min_gap):
    """True if candidate's artist appears within min_gap of the tail."""
    tail = ordered[-(min_gap - 1):] if min_gap > 0 else []
    return any(t["artist_id"] == candidate["artist_id"] for t in tail)


def interleave(tracks, min_gap):
    groups = group_by_artist(tracks)
    pools = sorted(groups.values(), key=len, reverse=True)
    ordered = []
    remaining = [t for pool in pools for t in pool]

    while remaining:
        placed = False
        for i, candidate in enumerate(remaining):
            if not violates_separation(ordered, candidate, min_gap):
                ordered.append(remaining.pop(i))
                placed = True
                break
        if not placed:
            ordered.append(remaining.pop(0))
    return ordered
