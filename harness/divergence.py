"""Prove that each seeded mutation actually changes behaviour.

Plan rev. 2 sec. 6.3. One originally-planned mutation -- swapping the operands
of abs(destination_zone - origin_zone) -- was behaviour-preserving, and was
caught only because an author happened to notice. A behaviour-preserving
"defect" is undetectable in principle and depresses measured recall equally
across every condition, so it adds noise to every comparison while looking
like a legitimate miss by the model.

Random fuzzing was tried first and rejected. These files take structured
records -- a ledger with balances and entries, a workspace with memberships,
a gateway object -- and randomly generated arguments fail their preconditions
so uniformly that both versions raise identically on every trial. That reports
"no divergence" for mutations that plainly do change behaviour: a false alarm
that blocks the build for the wrong reason. See witnesses.py, which holds one
hand-written valid call per file instead.

The witness value is compared across the correct and buggy modules; they must
differ, or the build aborts.
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from witnesses import WITNESSES

_COUNTER = [0]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _observe(module, witness):
    """Run the witness, capturing a return value or the exception it raised."""
    try:
        return ("ok", repr(witness(module)))
    except Exception as exc:
        return ("raise", "%s: %s" % (type(exc).__name__, exc))


def diverges(correct_path, buggy_path):
    """Return (changed, detail) for one correct/buggy pair."""
    fname = os.path.basename(correct_path)
    witness = WITNESSES.get(fname)
    if witness is None:
        return False, ("no divergence witness defined for %s -- add one to "
                       "harness/witnesses.py" % fname)

    _COUNTER[0] += 1
    tag = _COUNTER[0]
    mod_c = load_module(correct_path, "_dv_correct_%d" % tag)
    mod_b = load_module(buggy_path, "_dv_buggy_%d" % tag)

    got_c = _observe(mod_c, witness)
    got_b = _observe(mod_b, witness)

    if got_c == got_b:
        return False, "witness agrees: both give %s" % (got_c,)

    return True, "correct=%s buggy=%s" % (got_c, got_b)
