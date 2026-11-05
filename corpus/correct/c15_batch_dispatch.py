"""Batching job dispatch under concurrency and size limits."""


def chunk(items, batch_size):
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    for start in range(0, len(items), batch_size):
        yield items[start:start + batch_size]


def estimate_batch_bytes(batch, bytes_per_item):
    return len(batch) * bytes_per_item


def dispatch_all(client, jobs, batch_size, max_payload_bytes, bytes_per_item):
    accepted = []
    rejected = []
    for batch in chunk(jobs, batch_size):
        payload_bytes = estimate_batch_bytes(batch, bytes_per_item)
        if payload_bytes > max_payload_bytes:
            rejected.extend(batch)
            continue
        response = client.submit(batch)
        if response["status"] == "ok":
            accepted.extend(batch)
        else:
            rejected.extend(batch)
    return {"accepted": accepted, "rejected": rejected}
