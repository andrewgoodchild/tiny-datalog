#!/usr/bin/env python3
"""Lesson 24, exercise 3 — how sure, and why, in one pass.

Two ways to carry a confidence and its evidence together:

    product      (viterbi x why), componentwise: the best confidence,
                 and every minimal witness set, of *any* confidence
    best         the best confidence, and the witnesses of the
                 derivations that achieve it, and only those

Both are semirings.  They agree on the confidence and disagree on the
evidence, and the disagreement is the answer to the exercise.

Run:  python3 exercises/24-product-semiring.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tiny_datalog.semiring import (  # noqa: E402
    Semiring, SemiringEngine, ViterbiSemiring, WhySemiring)
from tiny_datalog.core import parse  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Product(Semiring):
    """The product of two semirings: pairs, with each operation applied
    to each half.  Always a semiring, because each half is one."""

    def __init__(self, a, b):
        self.a, self.b = a, b
        self.name = "%s*%s" % (a.name, b.name)
        self.zero = (a.zero, b.zero)
        self.one = (a.one, b.one)

    def plus(self, x, y):
        return (self.a.plus(x[0], y[0]), self.b.plus(x[1], y[1]))

    def times(self, x, y):
        return (self.a.times(x[0], y[0]), self.b.times(x[1], y[1]))

    def fact_value(self, pred, tup, weight):
        return (self.a.fact_value(pred, tup, weight),
                self.b.fact_value(pred, tup, weight))

    def fmt(self, v):
        return "%s, from %s" % (self.a.fmt(v[0]), self.b.fmt(v[1]))


class Best(Product):
    """Viterbi with its witnesses: `plus` keeps the pair with the higher
    confidence, and merges witnesses only on a tie.  A semiring because
    max is *selective* (it always returns one of its arguments) and
    multiplying by a positive confidence preserves which of two is
    larger — the lexicographic construction.  A confidence of 0 breaks
    that (it makes every pair tie), so weights here must be positive."""

    def plus(self, x, y):
        if x[0] > y[0]:
            return x
        if y[0] > x[0]:
            return y
        return (x[0], self.b.plus(x[1], y[1]))


def main():
    with open(os.path.join(ROOT, "programs", "memory-confidence.dl")) as fh:
        clauses = parse(fh.read())
    goal = ("user", "marco")
    for sr in (Product(ViterbiSemiring(), WhySemiring()),
               Best(ViterbiSemiring(), WhySemiring())):
        engine = SemiringEngine(clauses, sr).run()
        value = engine.value("reports_to", goal)
        print("%-8s reports_to(user, marco) = %s"
              % ("product" if type(sr) is Product else "best", sr.fmt(value)))


if __name__ == "__main__":
    main()
