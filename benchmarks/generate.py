#!/usr/bin/env python3
"""Generate scaled benchmark programs, so the course's asymptotic claims
become curves you can measure instead of take on faith.

    python3 benchmarks/generate.py chain 100 > chain100.dl
    python3 datalog.py --trace chain100.dl          # semi-naive deltas
    python3 datalog.py --naive --trace chain100.dl  # naive rederivation
    python3 datalog.py --magic --trace -q 'path(n1, X)' chain100.dl

Shapes:
    chain N    n1 -> n2 -> ... -> nN          (deep recursion, N rounds)
    tree N     complete binary tree, N nodes  (log-depth recursion)
    clique N   every ordered pair             (dense joins; keep N small!)
    grid N     N x N lattice, right/down      (many alternative paths)

Every program ships with the transitive-closure rules; add your own
queries.  Suggested experiment (Lesson 2): plot rounds and tuples
derived against N for chain vs tree, naive vs semi-naive vs magic.
"""

import argparse
import sys


def chain(n):
    return [("n%d" % i, "n%d" % (i + 1)) for i in range(1, n)]


def tree(n):
    return [("n%d" % (i // 2), "n%d" % i) for i in range(2, n + 1)]


def clique(n):
    return [("n%d" % i, "n%d" % j)
            for i in range(1, n + 1) for j in range(1, n + 1) if i != j]


def grid(n):
    edges = []
    for r in range(n):
        for c in range(n):
            if c + 1 < n:
                edges.append(("n%d_%d" % (r, c), "n%d_%d" % (r, c + 1)))
            if r + 1 < n:
                edges.append(("n%d_%d" % (r, c), "n%d_%d" % (r + 1, c)))
    return edges


def ontology(n):
    """Not edges: an EL ontology of n defined concepts in a chain of
    nested existentials, for subsumption.py.  Feed it to the classifier
    both ways and compare (Lesson 12):

        python3 benchmarks/generate.py ontology 300 > ont300.dl
        python3 subsumption.py ont300.dl            # compiled Datalog
        python3 subsumption.py --fast ont300.dl     # native saturation
    """
    lines = ["isa(b%d, base)." % i for i in range(10)]
    lines.append("define(c0, and(base, some(r, b0))).")
    lines += ["define(c%d, and(b%d, some(r, c%d)))." % (i, i % 10, i - 1)
              for i in range(1, n)]
    lines.append("role(r).")
    return lines


SHAPES = {"chain": chain, "tree": tree, "clique": clique, "grid": grid}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("shape", choices=sorted(SHAPES) + ["ontology"])
    ap.add_argument("n", type=int, help="size parameter")
    args = ap.parse_args(argv)

    if args.shape == "ontology":
        print("%% generated: ontology %d" % args.n)
        for line in ontology(args.n):
            print(line)
        return 0
    edges = SHAPES[args.shape](args.n)
    print("%% generated: %s %d  (%d edges)" % (args.shape, args.n, len(edges)))
    for a, b in edges:
        print("edge(%s, %s)." % (a, b))
    print()
    print("path(X, Y) :- edge(X, Y).")
    print("path(X, Z) :- edge(X, Y), path(Y, Z).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
