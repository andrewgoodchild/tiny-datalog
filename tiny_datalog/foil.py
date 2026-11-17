#!/usr/bin/env python3
"""
foil.py — learning rules from examples, the classic way: FOIL.
(Lesson 25.)

Every other module is handed rules and asked what follows.  This one is
handed what follows and asked for the rules.  That is **inductive logic
programming**: given background facts, some facts that should hold
(positive examples) and some that should not (negative examples), find
rules that derive all of the first and none of the second.

FOIL (Quinlan, 1990) searches for them greedily, in two nested loops:

* **The covering loop** builds a rule set.  Learn one rule that covers
  some positive examples and no negative ones; set aside the positives
  it covers; repeat until none are left.
* **The specialising loop** builds one rule.  Start with the most
  general rule there is, the bare head `target(X, Y)`, which covers
  everything.  Add the one body literal that best separates positive
  from negative, and repeat until no negative example is covered.

"Best" is **information gain**.  A rule under construction is judged by
its *bindings*: the substitutions that satisfy the body so far, each
labelled by whether its head is a positive example.  If p of them are
positive and n negative, saying "this binding is positive" takes
-log2(p / (p + n)) bits.  A literal that leaves p1 and n1, keeping t of
the old positive bindings alive, gains

    t * (log2(p1 / (p1 + n1)) - log2(p / (p + n)))

bits: how much purer the bindings became, times how many good ones
paid for it.

Two things are borrowed from the engine.  Trying a literal is one join
step (`Engine._join_step`, the step `substitutions` and why-not are
made of).  And the search space is cut by the safety check: `not` may
only use variables already bound, exactly as lesson 3 demands.

Recursion is where FOIL shows its age.  While a rule is being built,
a recursive literal such as `ancestor(Z, Y)` cannot be evaluated,
because the rules for `ancestor` do not exist yet.  FOIL looks it up in
the *examples* instead (extensional evaluation), which is only sound
when the positive examples are complete.  So the last step here is the
one FOIL lacked: the learned rules are run for real, and the answers
compared with the examples.

Examples come in lesson 27's expectations format: a fact is a positive
example, `:- fact.` a negative one.  With no negative examples the
world is taken as closed: every tuple over the program's constants
that is not a positive example is a negative one (lesson 4).

CLI
---
    python3 foil.py programs/kinship.dl --examples programs/grandparent.examples
    python3 foil.py programs/kinship.dl --examples programs/ancestor.examples -t

Exit status: 0, or 3 when the rules learned do not reproduce the
examples once they are run.
"""

from __future__ import annotations

import argparse
import itertools
import math
import sys

from tiny_datalog.core import (
    Atom, cli, Const, DatalogError, lint, Literal, parse, read_program,
    Rule, Var)
from tiny_datalog.diagnose import read_expectations, run

NAMES = "XYZUVWABCDEFGH"


# ---------------------------------------------------------------------------
# Examples
# ---------------------------------------------------------------------------

def read_examples(text, engine, limit=50000):
    """(target predicate, positive tuples, negative tuples, closed) from
    an examples file.  `closed` says the negatives were not given and
    are every other tuple over the program's constants."""
    true, false = read_expectations(text, engine.program.arity)
    preds = {p for p, _t in true} | {a.pred for a in false}
    if len(preds) != 1 or not true:
        raise DatalogError(
            "examples must be facts of one predicate, at least one of "
            "them positive (found: %s)" % (", ".join(sorted(preds)) or "none"))
    target = preds.pop()
    if any(r.head.pred == target for r in engine.program.rules):
        raise DatalogError("the program already has rules for %s; "
                           "learning it again proves nothing" % target)
    pos = {t for _p, t in true}
    neg = set()
    for atom in false:
        if any(isinstance(a, Var) for a in atom.args):
            raise DatalogError("a negative example is one ground fact: "
                               ":- %s." % atom)
        neg.add(tuple(a.value for a in atom.args))
    if len({len(t) for t in pos | neg}) != 1:
        raise DatalogError("the examples use %s with more than one arity"
                           % target)
    if pos & neg:
        raise DatalogError("an example is both positive and negative: %s"
                           % Atom(target, tuple(map(Const, min(pos & neg)))))
    if neg:
        return target, pos, neg, False
    domain = sorted({v for tuples in engine.rels.values() for t in tuples
                     for v in t} | {v for t in pos for v in t}, key=str)
    arity = len(next(iter(pos)))
    if len(domain) ** arity > limit:
        raise DatalogError(
            "the closed world has %d**%d tuples; give negative examples "
            "(`:- fact.`) instead" % (len(domain), arity))
    return target, pos, set(itertools.product(domain, repeat=arity)) - pos, True


# ---------------------------------------------------------------------------
# FOIL
# ---------------------------------------------------------------------------

def arities(rels):
    """{predicate: arity} for every relation with a tuple in it."""
    return {p: len(next(iter(ts))) for p, ts in rels.items() if ts}


class Foil:
    """One learning problem.  `rels` is the database literals are tried
    against: the program's facts and whatever its own rules derive
    (background knowledge), plus the positive examples standing in for
    the target relation, which is how a recursive literal is judged
    before the recursion exists."""

    def __init__(self, engine, target, pos, neg, max_body=4, trace=None):
        self.engine, self.target = engine, target
        self.pos, self.neg = set(pos), set(neg)
        self.max_body, self.trace = max_body, trace
        self.rels = {p: set(ts) for p, ts in engine.rels.items()}
        self.rels[target] = set(pos)
        self.arity = arities(self.rels)
        n = self.arity[target]
        self.head = Atom(target, tuple(Var(NAMES[i]) for i in range(n)))

    # -- bindings ----------------------------------------------------------

    def _seeds(self, examples):
        names = [a.name for a in self.head.args]
        return [dict(zip(names, tup)) for tup in sorted(examples, key=repr)]

    def _extend(self, substs, lit):
        return self.engine._join_step(
            lit, substs, self.rels.get(lit.atom.pred, ()))

    def covered(self, body, examples):
        """The examples a body covers: those with at least one binding
        that survives every literal."""
        substs = self._seeds(examples)
        for lit in body:
            substs = self._extend(substs, lit)
        return {self.engine.instantiate(self.head, s) for s in substs}

    # -- the search space ----------------------------------------------------

    def candidates(self, body, bound):
        """Every literal that could be added: each predicate over the
        variables bound so far and, for a positive literal, new ones.
        A literal must reuse a bound variable (or it says nothing about
        this rule's head), new variables are introduced in order (so no
        two candidates differ only by renaming), and `not` gets bound
        variables only, which is lesson 3's safety condition."""
        used = set(body) | {Literal(self.head)}
        for pred in sorted(self.arity):
            k = self.arity[pred]
            fresh = [n for n in NAMES if n not in bound][:k - 1]
            for names in itertools.product(bound + fresh, repeat=k):
                new = [n for n in dict.fromkeys(names) if n not in bound]
                if new != fresh[:len(new)] or len(new) == k \
                        or len(set(names)) < k \
                        or (new and pred == self.target):
                    continue
                atom = Atom(pred, tuple(Var(n) for n in names))
                if Literal(atom) not in used:
                    yield Literal(atom)
                # negating the target would be recursion through `not`
                if not new and pred != self.target \
                        and Literal(atom, True) not in used:
                    yield Literal(atom, True)

    # -- one rule ------------------------------------------------------------

    def _gain(self, pos, neg, lit, bound):
        pos1, neg1 = self._extend(pos, lit), self._extend(neg, lit)
        if not pos1:
            return None
        kept = len({tuple(s[v] for v in bound) for s in pos1})
        before = math.log2(len(pos) / (len(pos) + len(neg)))
        after = math.log2(len(pos1) / (len(pos1) + len(neg1)))
        return kept * (after - before), pos1, neg1, kept

    def learn_rule(self, remaining):
        """One rule covering some of `remaining` and no negative
        example, or None when no literal helps.  Greedy: the best
        literal is taken at each step and never reconsidered.

        The rule must also be safe, which sparse negative examples do
        not guarantee: `ancestor(X, Y) :- parent(X, Z).` may cover no
        negative example on file and still says Y is anybody at all.
        So once the negatives are gone the loop goes on until every
        head variable is bound, taking whichever binding literal keeps
        the most positive examples."""
        body = []
        bound = [a.name for a in self.head.args]
        pos, neg = self._seeds(remaining), self._seeds(self.neg)
        while True:
            loose = {v for v in bound[:len(self.head.args)]
                     if not any(Var(v) in lit.atom.args for lit in body
                                if not lit.negated)}
            if not neg and not loose:
                return self._prune(body)
            if len(body) == self.max_body:
                return None
            scored = []
            for lit in self.candidates(body, bound):
                result = self._gain(pos, neg, lit, bound)
                if result is None:
                    continue
                binds = not lit.negated and any(
                    a.name in loose for a in lit.atom.args)
                # with negatives left, rank by gain; with none, every
                # gain is zero, so rank by positive bindings kept
                if result[0] > 1e-9 if neg else binds:
                    scored.append((-result[0] if neg else -result[3],
                                   lit.negated, str(lit), lit, result))
            if not scored:
                return None
            scored.sort(key=lambda c: c[:3])
            if self.trace is not None:
                for _k, _n, text, _l, (g, p1, n1, _kept) in scored[:self.trace]:
                    print("     %-24s gain %6.2f   %d+ %d-"
                          % (text, g, len(p1), len(n1)))
            _key, _n, text, lit, (gain, pos, neg, _kept) = scored[0]
            print("   + %-24s gain %6.2f   %d+ %d-"
                  % (text, gain, len(pos), len(neg)))
            body.append(lit)
            bound += [a.name for a in lit.atom.args if a.name not in bound]

    def _prune(self, body):
        """Greedy search keeps a literal that later ones made
        unnecessary.  Drop any whose loss lets no negative example in
        and leaves the rule safe."""
        for lit in list(body):
            rest = [l for l in body if l is not lit]
            bound = {a.name for l in rest if not l.negated
                     for a in l.atom.args}
            safe = all(a.name in bound for a in self.head.args) and all(
                a.name in bound for l in rest if l.negated
                for a in l.atom.args)
            if rest and safe and not self.covered(rest, self.neg):
                print("   - %-24s no longer needed" % lit)
                body = rest
        return body

    # -- the rule set --------------------------------------------------------

    def learn(self):
        """(rules, positive examples left uncovered)."""
        rules, remaining = [], set(self.pos)
        while remaining:
            print("rule %d: %d positive example%s to cover"
                  % (len(rules) + 1, len(remaining),
                     "" if len(remaining) == 1 else "s"))
            body = self.learn_rule(remaining)
            if body is None:
                print("   no literal separates what is left: giving up")
                break
            rule = Rule(self.head, tuple(body))
            got = self.covered(body, remaining)
            print("   %s   covers %d" % (rule, len(got)))
            rules.append(rule)
            remaining -= got
        return rules, remaining


def check(clauses, rules, target, pos, neg):
    """Run the learned rules for real: (positives derived, negatives
    derived).  The search judged recursive literals against the
    examples; this judges the rules against themselves."""
    got, bad, _broken = _check(clauses, rules, target, pos, neg)
    return got, bad


def _check(clauses, rules, target, pos, neg):
    engine = run(list(clauses) + list(rules))
    derived = engine.rels.get(target, set())
    return derived & pos, derived & neg, engine.violations()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def report(clauses, rules, target, pos, neg):
    """Print the learned rules and what they do when run; True if they
    reproduce the examples and break none of the program's integrity
    constraints, which the search never looked at."""
    print("learned %d rule%s:" % (len(rules), "" if len(rules) == 1 else "s"))
    for rule in rules:
        print("   %s" % rule)
    known = set(lint(clauses))
    for warning in lint(list(clauses) + list(rules)):
        if warning not in known:
            print(warning)                  # lesson 17's, on what was learned
    got, bad, broken = _check(clauses, rules, target, pos, neg)
    print("run for real: %d of %d positive examples derived, %d of %d "
          "negative" % (len(got), len(pos), len(bad), len(neg)))
    before = {str(c) for c, _substs in run(clauses).violations()}
    broken = [str(c) for c, _substs in broken if str(c) not in before]
    for constraint in broken:               # the program's own tests
        print("violates the program's constraint: %s" % constraint)
    return got == pos and not bad and not broken


@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Learn rules for one predicate from examples (FOIL).")
    ap.add_argument("file", help="background facts (and rules)")
    ap.add_argument("--examples", required=True, metavar="FILE",
                    help="facts are positive examples, `:- fact.` negative; "
                         "with no negatives the world is closed")
    ap.add_argument("--max-body", type=int, default=4, metavar="N",
                    help="longest rule body to try (default 4)")
    ap.add_argument("-t", "--trace", action="store_true",
                    help="show the five best candidates at every step")
    args = ap.parse_args(argv)

    clauses = parse(read_program(args.file))
    engine = run(clauses)
    target, pos, neg, closed = read_examples(read_program(args.examples),
                                             engine)
    print("target %s/%d: %d positive examples, %d negative%s"
          % (target, len(next(iter(pos))), len(pos), len(neg),
             " (closed world)" if closed else ""))
    foil = Foil(engine, target, pos, neg, args.max_body,
                5 if args.trace else None)
    rules, _left = foil.learn()
    return 0 if report(clauses, rules, target, pos, neg) else 3


if __name__ == "__main__":
    sys.exit(main())
