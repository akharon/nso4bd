"""Hand-written divergence witnesses: one valid call per seeded mutation.

Plan rev. 2 sec. 6.3 requires proof that each mutation actually changes
behaviour, so that a behaviour-preserving "defect" -- undetectable in
principle, and depressing recall equally across every condition -- can never
enter the corpus unnoticed.

Random fuzzing was tried first and rejected: these functions take structured
records (a ledger with balances and entries, a workspace with members, a
transition history), and randomly generated dicts fail their preconditions so
uniformly that both versions raise identically on every trial. That produces
"no divergence" for mutations that plainly do change behaviour -- a false
alarm that would have blocked the build for the wrong reason.

Each entry below is therefore an explicit, minimal call that exercises the
mutated line on valid input. WITNESSES maps a correct-corpus filename to a
callable taking the loaded module and returning some observable value; the
build compares that value across the correct and buggy modules and requires
them to differ.
"""


def _c01(m):
    src = {"id": "L1", "destination_hub": "h1",
           "queued": list(range(10))}
    dst = {"id": "L2", "destination_hub": "h2", "queued": [99]}
    moved = m.rebalance(src, dst, 3)
    return moved, src["queued"], dst["queued"]


class _Gateway:
    def refund(self, charge_id, amount_cents, idempotency_key):
        return {"id": "rcpt-1"}


def _c02(m):
    order = {
        "id": "ord-1",
        "charge_id": "ch-1",
        "idempotency_key": "idem-1",
        "line_items": [{"id": "li-1", "unit_price_cents": 500,
                        "quantity": 1}],
        "audit": [],
    }
    m.issue_refund(_Gateway(), order, "li-1", 250, "user-1")
    return order["audit"]


def _c03(m):
    return m.moving_average([1.0, 2.0, 3.0, 4.0, 5.0], 2)


def _c04(m):
    bucket = m.TokenBucket(capacity_tokens=10, refill_per_second=2.0)
    bucket.tokens = 1.0
    bucket.last_refill_at = 0.0
    return round(bucket.seconds_until_available(5.0, now_seconds=0.0), 6)


def _c05(m):
    workspace = {"memberships": {"u1": {"role": "admin"}}}
    try:
        return ("ok", m.can_grant(workspace, "stranger", "viewer"))
    except Exception as exc:
        return ("raise", type(exc).__name__)


def _c06(m):
    return round(m.irradiance_kwh_per_m2(-3.0, 0.0), 6)


def _c07(m):
    vehicle = {"lat": 0.0, "lon": 0.0}
    fence = {"center_lat": 0.0, "center_lon": 0.0, "radius_m": 100.0}
    return m.within_fence(vehicle, fence)


def _c08(m):
    calls = {"n": 0}

    def always_fails():
        calls["n"] += 1
        raise m.TransientError("boom")

    slept = []
    try:
        m.call_with_retry(always_fails, max_attempts=3,
                          base_delay_seconds=1.0, max_delay_seconds=10.0,
                          sleeper=slept.append)
    except Exception:
        pass
    # The seeded defect removes the final-attempt guard, so the loop sleeps
    # once more than it should. Count sleeps, not delays: the delays are
    # randomised and would differ between runs regardless of the mutation.
    return calls["n"], len(slept)


def _c09(m):
    order = {"state": "draft"}
    history = []
    ok = m.apply_transition(order, "submitted", history)
    return ok, order["state"], history


def _c10(m):
    tenants = {
        "t1": {"org_id": "org-1"},
        "t2": {"org_id": "org-1"},
        "t3": {"org_id": "org-2"},
    }
    return sorted(m.sibling_tenants("t1", tenants))


def _c11(m):
    workspace = {"members": {"m1": {"id": "m1"}, "m2": {"id": "m2"},
                             "m3": {"id": "m3"}}}
    return m.page_of_members(workspace, 1, 2)


def _c12(m):
    return m.run_cycle(sensor_fahrenheit=212.0, setpoint_celsius=50.0,
                       hysteresis_celsius=1.0)


def _c13(m):
    ledger = {"balances": {"acct-a": 1000, "acct-b": 0}, "entries": []}
    result = m.transfer(ledger, "acct-a", "acct-b", 250, "test")
    return result, ledger["balances"]


def _c14(m):
    ordered = [{"id": 1, "artist_id": "X"}, {"id": 2, "artist_id": "Y"}]
    candidate = {"id": 3, "artist_id": "X"}
    # min_gap=2 must see both tail entries; the seeded off-by-one shortens the
    # window to one, so X is no longer detected as too close.
    return m.violates_separation(ordered, candidate, 2)


class _Client:
    def submit(self, batch):
        return {"status": "ok"}


def _c15(m):
    jobs = [{"id": i} for i in range(6)]
    return m.dispatch_all(_Client(), jobs, batch_size=3,
                          max_payload_bytes=1000, bytes_per_item=400)


WITNESSES = {
    "c01_lane_routing.py": _c01,
    "c02_order_refund.py": _c02,
    "c03_sensor_window.py": _c03,
    "c04_rate_limiter.py": _c04,
    "c05_permission_grant.py": _c05,
    "c06_solar_yield.py": _c06,
    "c07_geo_fence.py": _c07,
    "c08_retry_backoff.py": _c08,
    "c09_state_machine.py": _c09,
    "c10_tenant_lookup.py": _c10,
    "c11_member_roster.py": _c11,
    "c12_temperature_control.py": _c12,
    "c13_audit_transfer.py": _c13,
    "c14_playlist_shuffle.py": _c14,
    "c15_batch_dispatch.py": _c15,
}
