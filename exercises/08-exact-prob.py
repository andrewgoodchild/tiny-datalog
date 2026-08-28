#!/usr/bin/env python3
"""Lesson 8, exercise 3 — the exact probability that s reaches t in
programs/prob-reach.dl, by enumerating all 2^5 worlds (each link
independently up with its @ probability).

The Viterbi semiring reports the best single route; the exact value
must be at least that, because "some route works" includes "the best
route works".  Run:

    python3 exercises/08-exact-prob.py
"""

import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from semiring import run_semiring  # noqa: E402

LINKS = {("s", "a"): 0.9, ("a", "t"): 0.9, ("s", "b"): 0.5,
         ("b", "t"): 0.95, ("a", "b"): 0.8}


def reaches(up):
    """Does s reach t using only the up links?"""
    frontier, seen = {"s"}, {"s"}
    while frontier:
        nxt = {b for (a, b) in up if a in frontier and b not in seen}
        seen |= nxt
        frontier = nxt
    return "t" in seen


def exact_probability():
    total = 0.0
    links = list(LINKS)
    for states in itertools.product([True, False], repeat=len(links)):
        up = {l for l, s in zip(links, states) if s}
        p = 1.0
        for l, s in zip(links, states):
            p *= LINKS[l] if s else 1 - LINKS[l]
        if reaches(up):
            total += p
    return total


def viterbi_value():
    text = "".join("link(%s, %s) @ %s.\n" % (a, b, p)
                   for (a, b), p in LINKS.items())
    text += ("reach(X, Y) :- link(X, Y).\n"
             "reach(X, Z) :- link(X, Y), reach(Y, Z).\n")
    return run_semiring(text, "viterbi").value("reach", ("s", "t"))


if __name__ == "__main__":
    exact = exact_probability()
    best = viterbi_value()
    print("exact P(s reaches t)  = %.6f   (enumeration over 32 worlds)" % exact)
    print("Viterbi (best route)  = %.6f" % best)
    print("exact >= Viterbi: %s" % (exact >= best))
