#!/usr/bin/env python3
"""Lesson 7, the specialisation exercises — is "materialise provenance
once, specialise later" sound?

Checks two candidate maps out of why-provenance:

    why -> minplus   a semiring homomorphism; agrees everywhere
    why -> count     no homomorphism exists; a counterexample proves it

Run:  python3 exercises/07-homomorphism.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from semiring import run_semiring  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def load(name):
    with open(os.path.join(ROOT, "programs", name)) as fh:
        return fh.read()


def fact_weights(text):
    """The @-weight of every base fact, keyed by its printed form."""
    weights = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\w+\([^)]*\))\s*@\s*([0-9.]+)\s*\.", line)
        if m:
            atom = re.sub(r",\s*", ", ", m.group(1))
            weights[atom] = float(m.group(2))
    return weights


def h_minplus(why_value, weights):
    """why -> minplus: a witness set costs the sum of its facts; a set of
    alternative witnesses costs the cheapest of them.  This respects
    both operations — why's `plus` is set union (becomes min) and its
    `times` is pairwise union (becomes +) — so it is a homomorphism."""
    if not why_value:
        return float("inf")
    return min(sum(weights[f] for f in witness) for witness in why_value)


def check_minplus():
    text = load("routes.dl")
    weights = fact_weights(text)
    why = run_semiring(text, "why")
    direct = run_semiring(text, "minplus")
    print("why -> minplus, over 06-routes.dl:")
    ok = True
    for pred in sorted(why.idb):
        for tup in sorted(why.rels.get(pred, {})):
            specialised = h_minplus(why.value(pred, tup), weights)
            computed = direct.value(pred, tup)
            flag = "ok" if abs(specialised - computed) < 1e-9 else "MISMATCH"
            ok &= flag == "ok"
            label = "%s(%s)" % (pred, ", ".join(str(v) for v in tup))
            print("  %-14s h(why)=%-4g  minplus=%-4g  %s"
                  % (label, specialised, computed, flag))
    print("  => %s\n" % ("agrees on every fact" if ok else "FAILED"))
    return ok


def check_count():
    text = load("two-derivations.dl")
    why = run_semiring(text, "why")
    count = run_semiring(text, "count")
    witnesses = why.value("q", ("a", "c"))
    derivations = count.value("q", ("a", "c"))
    print("why -> count, over 06-two-derivations.dl:")
    print("  q(a, c) why   = %s" % " | ".join(
        "{%s}" % ", ".join(sorted(w)) for w in witnesses))
    print("  q(a, c) count = %d" % derivations)
    print("  p(a, c) why   = %s" % " | ".join(
        "{%s}" % ", ".join(sorted(w)) for w in why.value("p", ("a", "c"))))
    print("  p(a, c) count = %d" % count.value("p", ("a", "c")))
    broken = (len(witnesses) == 1 and derivations == 2)
    print("  => q and p have IDENTICAL why-values but different counts: %s"
          % broken)
    print("     so no function of the why-value can produce the count —")
    print("     why-provenance is absorptive and has discarded multiplicity.")
    return broken


if __name__ == "__main__":
    a = check_minplus()
    b = check_count()
    sys.exit(0 if (a and b) else 1)
