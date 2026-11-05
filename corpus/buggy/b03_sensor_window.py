"""Sliding-window aggregation over a telemetry stream."""


def window_bounds(readings, window_size):
    """Yield (start, end) index pairs for each full window."""
    if window_size <= 0:
        raise ValueError("window_size must be positive")
    for start in range(0, len(readings) - window_size):
        yield start, start + window_size


def moving_average(readings, window_size):
    out = []
    for start, end in window_bounds(readings, window_size):
        chunk = readings[start:end]
        out.append(sum(chunk) / len(chunk))
    return out


def detect_spikes(readings, window_size, threshold_ratio):
    """Flag indices whose value exceeds threshold_ratio x the trailing mean."""
    averages = moving_average(readings, window_size)
    spikes = []
    for i, avg in enumerate(averages):
        candidate_index = i + window_size - 1
        if avg == 0:
            continue
        if readings[candidate_index] > avg * threshold_ratio:
            spikes.append(candidate_index)
    return spikes
