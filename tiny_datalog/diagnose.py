#!/usr/bin/env python3
"""
diagnose.py — from a wrong answer to the rule at fault, by algorithmic
debugging.  (Lesson 27; mutation.py is the lesson's other half.)

`--explain` prints why a fact was derived and leaves a person to read
the tree and spot the bad step.  This module does the reading.  It
needs to be told what *should* be true, and there are four ways to say
so, which can be mixed:

* `--wrong FACT` / `--missing FACT`: one symptom, stated on the spot;
* `--expect FILE`: an **expectations** file, in the language itself.  A
  fact must be derived, and `:- fact.` (variables allowed) must never
  be.  It has to be a separate file: a fact written into the program
  would simply become true;
* `--against FILE`: a **reference** program, such as the version before
  a refactor.  Every predicate it defines is judged by its answers;
* `--ask`: anything still unknown is put to you as a yes/no question.

Together they are an **oracle** for the *intended interpretation*: the
set of facts the author had in mind.  A program is wrong exactly where
its model differs from that set, and Shapiro's **algorithmic
debugging** (1982) turns each difference into a culprit:

* **A wrong answer** (derived, but false).  Take its derivation.  If
  some premise is false too, the fault is further down: move to that
  premise.  If every premise is true, this rule made a false
  conclusion out of true premises, and *the rule is wrong*.
* **A missing answer** (true, but not derived).  Look for a rule and a
  substitution whose body is true in the intended interpretation.  If
  one exists, some body fact is missing too (or, under `not`, wrongly
  present): move there.  If none exists, the fact is **uncovered**:
  no rule could ever derive it from true facts, so a rule is missing
  or too strict.

The two call each other through negation: a premise `not q(a)` is
false when q(a) should hold, which is a missing answer.

Where the oracle is silent the debugger does not guess.  The data is
taken as given (a stated fact is true; an unstated fact of a predicate
with no rules is false, which is lesson 4's closed world).  A *derived*
fact nobody has vouched for stops the search with "unless the fault is
one step further down", which names the next question to answer.

CLI
---
    python3 diagnose.py programs/lending-draft2.dl --wrong 'may_borrow(kim)'
    python3 diagnose.py programs/access-draft.dl --expect programs/access.expect
    python3 diagnose.py programs/access-draft.dl --against programs/access.dl

Exit status: 0, or 3 when a wrong or missing answer was found.
"""

from __future__ import annotations

import argparse
import sys
from collections import namedtuple
from tiny_datalog.core import (
    aggregate_of, Atom, body_order, check_query_atom, cli, Const,
    DatalogError, format_atom, is_comparison, match, parse,
    parse_query_atom, read_program, sort_key, Var)
from tiny_datalog.datalog import _derivation_of, Engine, Program


# ---------------------------------------------------------------------------
# The oracle: what should be true
# ---------------------------------------------------------------------------

def read_expectations(text, arity=None):
    """(facts that must hold, atoms that must not) from an expectations
    file.  Kept to single atoms on purpose: a failed expectation then
    names one fact, which is where diagnosis starts.  A property over
    several facts is an integrity constraint, and belongs in the
    program (lesson 17)."""
    true, false = set(), []
    for c in parse(text):
        denial = c.constraint and len(c.body) == 1 \
            and not c.body[0].negated and not is_comparison(c.body[0])
        atom = c.body[0].atom if denial else c.head
        if not denial and (c.body or c.constraint or c.retract or any(
                isinstance(a, Var) for a in atom.args)):
            raise DatalogError(
                "an expectation is a ground fact (it must hold) or "
                "`:- fact.` (it must not): %s" % c)
        check_query_atom(atom, arity)       # arity, no compound terms
        if denial:
            false.append(atom)
        else:
            true.add((atom.pred, tuple(a.value for a in atom.args)))
    return true, false


class Oracle:
    """The intended interpretation, as far as anybody has stated it.

    Calling it gives a verdict on one ground fact: True, False, or None
    for "nobody has said".  `world` is the same knowledge as a database
    a rule body can be run against: the program's own answers,
    corrected by everything known."""

    def __init__(self, engine, true=(), false=(), reference=None, ask=None):
        self.engine, self.reference, self.ask = engine, reference, ask
        self.true, self.false = set(true), list(false)
        self.judged = set(reference.program.arity) if reference else set()
        self.index = {}                     # _derivation_of's lookup cache
        self.world = Engine(engine.program)
        for pred, tuples in engine.rels.items():
            self.world.rels[pred] = set(tuples)
        for pred in self.judged:
            self.world.rels[pred] = set(reference.rels.get(pred, ()))
        for pred, tup in self.true:
            self.world.rels[pred].add(tup)
        for atom in self.false:
            self.world.rels[atom.pred] -= set(self._denied(atom))

    def _denied(self, atom, rels=None):
        rels = self.world.rels if rels is None else rels
        return [t for t in rels.get(atom.pred, ())
                if match(atom.args, t, {}) is not None]

    def __call__(self, pred, tup):
        if (pred, tup) in self.true:
            return True
        if any(a.pred == pred and match(a.args, tup, {}) is not None
               for a in self.false):
            return False
        if pred in self.judged:
            return tup in self.reference.rels.get(pred, ())
        if self.engine.first_seen.get((pred, tup)) == 0:
            return True                     # stated in the program
        if pred not in self.engine.program.idb:
            return False                    # data nobody stated
        answer = self.ask(format_atom(pred, tup)) if self.ask else None
        if answer:
            self.true.add((pred, tup))
            self.world.rels[pred].add(tup)
        elif answer is not None:
            self.false.append(Atom(pred, tuple(Const(v) for v in tup)))
            self.world.rels[pred].discard(tup)
        return answer

    def symptoms(self):
        """(wrong answers, missing answers), each a sorted list of
        (pred, tuple): where the program and the oracle disagree."""
        rels = self.engine.rels
        wrong = {(a.pred, t) for a in self.false
                 for t in self._denied(a, rels)}
        missing = {(p, t) for p, t in self.true if t not in rels.get(p, ())}
        for pred in self.judged:
            mine = rels.get(pred, set())
            theirs = self.reference.rels.get(pred, set())
            wrong |= {(pred, t) for t in mine - theirs}
            missing |= {(pred, t) for t in theirs - mine}
        order = lambda f: (f[0], sort_key(f[1]))
        return sorted(wrong, key=order), sorted(missing, key=order)


# ---------------------------------------------------------------------------
# Algorithmic debugging
# ---------------------------------------------------------------------------

# kind: "rule" (a wrong rule), "unsure" (that rule, unless one of
# `unsure` is wrong too), "uncovered" (no rule's body is true for it),
# "fact" (a stated fact that is false), "absent" (a fact nobody stated,
# of a predicate with no rules), "aggregate" (the search stops at an
# aggregate: its group is --explain's to show).
Finding = namedtuple("Finding", "kind rule pred tup subst unsure trail")


def locate(oracle, kind, pred, tup):
    """From one symptom, "wrong" or "missing", to a Finding.  A loop,
    not a recursion: each step either ends the search or names the next
    fact to suspect, and a long chain must not meet Python's recursion
    limit.  `seen` stops two facts blaming each other for ever."""
    trail, seen = [], set()
    while True:
        seen.add((kind, pred, tup))
        step = (_wrong_step if kind == "wrong" else _missing_step)(
            oracle, pred, tup, trail, seen)
        if isinstance(step, Finding):
            return step
        kind, pred, tup = step


def _wrong_step(oracle, pred, tup, trail, seen):
    """pred(tup) is derived and false.  Its derivation has a false
    premise (go there), or it does not (this rule is the culprit)."""
    label = format_atom(pred, tup)
    derivation = _derivation_of(oracle.engine, pred, tup, oracle.index)
    if derivation is None:
        trail.append("%s should not hold, and the program states it" % label)
        return Finding("fact", None, pred, tup, None, [], trail)
    rule, premises = derivation
    trail.append("%s should not hold   [via %s]" % (label, rule))
    if aggregate_of(rule.head):
        return Finding("aggregate", rule, pred, tup, None, [], trail)
    unsure = []
    for lit, t in premises:
        if is_comparison(lit):
            continue
        verdict = oracle(lit.atom.pred, t)
        if lit.negated:
            if verdict and ("missing", lit.atom.pred, t) not in seen:
                return "missing", lit.atom.pred, t
            if verdict is None:
                unsure.append("%s is missing"
                              % format_atom(lit.atom.pred, t))
        elif verdict is False:
            return "wrong", lit.atom.pred, t
        elif verdict is None:
            unsure.append("%s is wrong" % format_atom(lit.atom.pred, t))
    subst = match(rule.head.args, tup, {})
    for lit, t in premises:
        subst = match(lit.atom.args, t, subst) or subst
    return Finding("unsure" if unsure else "rule", rule, pred, tup,
                   subst, unsure, trail)


def _missing_step(oracle, pred, tup, trail, seen):
    """pred(tup) is true and not derived.  Find a rule whose body is
    true in the intended interpretation: one of its body facts is
    missing as well (or wrongly present, under `not`), so go there.  If
    no rule has such a body, the fact is uncovered."""
    engine, label = oracle.engine, format_atom(pred, tup)
    rules = [r for r in engine.program.rules if r.head.pred == pred]
    if not rules:
        trail.append("%s should hold, and no rule derives %s"
                     % (label, pred))
        return Finding("absent", None, pred, tup, None, [], trail)
    for rule in rules:
        seed = match(rule.head.args, tup, {})
        if aggregate_of(rule.head) or seed is None:
            continue
        found = oracle.world.substitutions(rule, seed=seed)
        for s in sorted(found, key=lambda s: sort_key(
                [s[k] for k in sorted(s)])):
            for lit in rule.body:
                if is_comparison(lit):
                    continue
                t = Engine.instantiate(lit.atom, s)
                here = t in engine.rels.get(lit.atom.pred, ())
                if here != lit.negated:
                    continue            # this premise is as it should be
                step = ("wrong" if lit.negated else "missing",
                        lit.atom.pred, t)
                if step in seen:
                    break               # a cycle: try the next solution
                trail.append("%s should hold   [via %s]" % (label, rule))
                return step
    # Nothing known makes a body true.  Before blaming these rules, see
    # where each one's join died (as why-not does): a blocker the oracle
    # cannot judge may be the real fault, one level down.
    unsure = []
    for rule in rules:
        seed = match(rule.head.args, tup, {})
        blocked = None if aggregate_of(rule.head) or seed is None \
            else _blocker(engine, rule, seed)
        if blocked is None or blocked[0].atom.pred in oracle.judged \
                or blocked[0].atom.pred not in engine.program.idb:
            continue                    # data and comparisons: as given
        lit, s = blocked
        atom = Atom(lit.atom.pred, tuple(
            Const(s[a.name]) if isinstance(a, Var) and a.name in s else a
            for a in lit.atom.args))
        kind = "wrong" if lit.negated else "missing"
        verdict = None
        if all(isinstance(a, Const) for a in atom.args):
            t = tuple(a.value for a in atom.args)
            verdict = oracle(atom.pred, t)
            if verdict == (not lit.negated) and (kind, atom.pred, t) \
                    not in seen:
                trail.append("%s should hold   [via %s]" % (label, rule))
                return kind, atom.pred, t
        if verdict is None:
            unsure.append("%s is %s" % (atom, kind))
    trail.append("%s should hold, and no rule for %s/%d has a true body"
                 % (label, pred, len(tup)))
    return Finding("uncovered", None, pred, tup, None, unsure, trail)


def _blocker(engine, rule, seed):
    """(literal, substitution so far) where the program's own join for
    this rule and head dies, or None if it does not."""
    substs = [dict(seed)]
    for i in body_order(rule.body):
        lit = rule.body[i]
        survivors = engine._join_step(
            lit, substs, engine.rels.get(lit.atom.pred, ()))
        if not survivors:
            return lit, substs[0]
        substs = survivors
    return None


def diagnose(oracle, symptoms=None):
    """Every symptom (or just the `symptoms` given, as a (wrong,
    missing) pair) traced to its culprit, and symptoms sharing a
    culprit grouped: [(Finding, wrong, missing)], where the Finding is
    the group's shortest trail and the other two are lists of facts."""
    wrong, missing = symptoms or oracle.symptoms()
    groups = {}
    for kind, facts in (("wrong", wrong), ("missing", missing)):
        for pred, tup in facts:
            f = locate(oracle, kind, pred, tup)
            key = (f.kind, f.rule, None if f.rule else f.pred,
                   f.tup if f.kind in ("fact", "absent") else None)
            g = groups.setdefault(key, [f, [], []])
            if len(f.trail) < len(g[0].trail):
                g[0] = f
            g[1 if kind == "wrong" else 2].append((pred, tup))
    return [tuple(g) for g in groups.values()]


def _bindings(subst):
    return ", ".join("%s = %s" % (k, Const(v)) for k, v in sorted(
        subst.items()) if not k.startswith("_#"))


def verdict_lines(f):
    """A Finding as text: the trail of blame, then the conclusion."""
    out = ["  " * i + line for i, line in enumerate(f.trail)]
    label = format_atom(f.pred, f.tup)
    if f.kind in ("rule", "unsure"):
        out += ["=> the rule at fault: %s" % f.rule,
                "   its body is true and its head is false at %s"
                % _bindings(f.subst)]
    elif f.kind == "uncovered":
        out.append("=> a rule for %s/%d is missing, or one is too strict: "
                   "nothing true implies %s" % (f.pred, len(f.tup), label))
    elif f.kind == "fact":
        out.append("=> the data is wrong, not a rule: %s is stated" % label)
    elif f.kind == "absent":
        out.append("=> the data is incomplete, not a rule: %s is not "
                   "stated" % label)
    else:
        out.append("=> an aggregate decides this; --explain %s shows "
                   "its group" % label)
    if f.unsure:
        out.append("   unless the fault is one step further down (settle "
                   "it with --expect or --ask): %s" % ", ".join(f.unsure))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run(clauses):
    """Evaluate parsed clauses with the base engine."""
    engine = Engine(Program(clauses))
    engine.run()
    return engine


def _ask(question):
    """Put one yes/no question on the terminal; None at end of input."""
    while True:
        sys.stdout.write("is %s true? [y/n] " % question)
        sys.stdout.flush()
        line = sys.stdin.readline()
        if not line:
            print()
            return None
        if not sys.stdin.isatty():
            print(line.strip())         # keep a piped transcript readable
        if line.strip().lower() in ("y", "yes", "n", "no"):
            return line.strip().lower().startswith("y")


def _ground_fact(text, arity):
    atom = parse_query_atom(text, arity)
    if any(isinstance(a, Var) for a in atom.args):
        raise DatalogError("a symptom is one ground fact: %s" % atom)
    return atom


@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Trace wrong and missing answers to the rule at "
                    "fault (algorithmic debugging).")
    ap.add_argument("file", help="the program under test")
    ap.add_argument("--expect", metavar="FILE",
                    help="expectations: facts that must hold, and "
                         "`:- fact.` for facts that must not")
    ap.add_argument("--against", metavar="FILE",
                    help="a reference program whose answers are right")
    ap.add_argument("--wrong", action="append", default=[], metavar="FACT",
                    help="a derived fact that should not hold")
    ap.add_argument("--missing", action="append", default=[], metavar="FACT",
                    help="a fact that should hold and is not derived")
    ap.add_argument("--ask", action="store_true",
                    help="answer y/n about facts the oracle cannot judge")
    args = ap.parse_args(argv)

    clauses = parse(read_program(args.file))
    engine = run(clauses)
    arity = engine.program.arity
    true, false = (read_expectations(read_program(args.expect), arity)
                   if args.expect else (set(), []))
    named = ([], [])                    # symptoms given on the command line
    for i, texts in enumerate((args.wrong, args.missing)):
        for atom in (_ground_fact(q, arity) for q in texts):
            fact = atom.pred, tuple(a.value for a in atom.args)
            if (fact[1] in engine.rels.get(atom.pred, ())) == bool(i):
                raise DatalogError("%s is %sderived, so it cannot be a %s "
                                   "answer" % (atom, "" if i else "not ",
                                               "missing" if i else "wrong"))
            named[i].append(fact)
            true.add(fact) if i else false.append(atom)
    reference = run(parse(read_program(args.against))) \
        if args.against else None
    for i, facts in enumerate(named):
        for pred, tup in facts:
            if reference and pred in reference.program.arity and (
                    tup in reference.rels.get(pred, ())) != bool(i):
                raise DatalogError(
                    "%s is called %s, but %s %s it" % (
                        format_atom(pred, tup), "missing" if i else "wrong",
                        args.against, "does not derive" if i else "derives"))
    if not (true or false or reference):
        ap.error("say what should be true: --expect, --against, "
                 "--wrong or --missing")
    oracle = Oracle(engine, true, false, reference,
                    _ask if args.ask else None)
    wrong, missing = named if any(named) else oracle.symptoms()
    print("%d wrong answer%s, %d missing"
          % (len(wrong), "" if len(wrong) == 1 else "s", len(missing)))
    if not (wrong or missing):
        print("the program agrees with everything stated, on these facts")
        return 0
    for finding, bad, lost in diagnose(oracle, (wrong, missing)):
        print()
        for kind, facts in (("wrong", bad), ("missing", lost)):
            if facts:
                shown = ", ".join(format_atom(p, t) for p, t in facts[:3])
                print("%s: %s%s" % (kind, shown, "" if len(facts) <= 3 else
                                    ", and %d more" % (len(facts) - 3)))
        for line in verdict_lines(finding):
            print("   " + line)
    return 3


if __name__ == "__main__":
    sys.exit(main())
