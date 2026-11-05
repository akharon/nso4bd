"""Order state machine with a guarded transition table."""

TRANSITIONS = {
    "draft": ("submitted", "cancelled"),
    "submitted": ("approved", "rejected", "cancelled"),
    "approved": ("fulfilled", "cancelled"),
    "rejected": (),
    "fulfilled": (),
    "cancelled": (),
}

TERMINAL = ("fulfilled", "rejected", "cancelled")


def can_transition(current, target):
    return target in TRANSITIONS.get(current, ())


def is_terminal(state):
    return state in TERMINAL


def apply_transition(order, target, history):
    current = order["state"]
    if is_terminal(current):
        return False
    if not can_transition(current, target):
        return False

    order["state"] = target
    history.append((current, target))
    return True


def replay(initial_state, targets):
    """Apply a sequence of transitions, stopping at the first rejected one."""
    order = {"state": initial_state}
    history = []
    for target in targets:
        if not apply_transition(order, target, history):
            break
    return order["state"], history
