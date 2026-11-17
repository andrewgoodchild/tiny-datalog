#!/usr/bin/env python3
"""
synthesis.py — learning rules as rule *selection*, guided by
provenance.  (Lesson 26.)

FOIL (lesson 25) builds one rule at a time, one literal at a time, and
never looks back.  The approach here, after ProSynth (Raghothaman,
Mendelson, Zhao, Naik and Scholz, POPL 2020), turns the problem round:

1. Write down every rule that *might* be in the answer: the
   **candidates**.  Now a program is a subset of them, and learning is
   choosing one switch per candidate, on or off.
2. Let a SAT solver propose a subset.
3. Run it, for real, on the real engine.  If it reproduces the
   examples, stop.
4. Otherwise ask the engine *why* it failed, turn the reason into a
   constraint on the switches that rules out this subset and many
   others like it, and go back to 2.

The loop is counterexample-guided inductive synthesis; the lesson is
in step 4, where the two kinds of failure each have a provenance:

* **A wrong answer** (a negative example was derived).  Its
  **why-provenance** over rules is the minimal sets of rules that
  suffice to derive it.  For each such set: never those together.
  That is lesson 8's why semiring with one change, the tokens are
  rules where they were facts, which takes one extra body literal per
  candidate and six lines of semiring.
* **A missing answer** (a positive example was not derived).  A
  positive program is monotone: adding rules never removes an answer.
  So keep switching more candidates on for as long as the answer
  stays missing.  What is left off at the end is a **why-not**
  explanation: at least one of those must come on.

Each constraint is a clause, and the solver (sat.py) is forty lines of
DPLL.  It tries "off" first, so the subset it proposes is a small one.

What this buys over FOIL: recursion is evaluated, not looked up, so a
handful of examples will do and no rule can fool the search by citing
the examples; and the search backtracks, so an unhelpful first literal
costs nothing.  What it costs: the candidates must be enumerated, and
there are many.  `--max-body` and `--vars` bound them, containment
(lesson 16) removes the redundant ones, and `--candidates FILE` takes
them from a file instead, written by a person or by a language model.

Positive rules only: monotonicity is what makes a why-not clause
sound, and `not` breaks it.

CLI
---
    python3 synthesis.py programs/kinship.dl --examples programs/ancestor-sparse.examples
    python3 synthesis.py programs/kinship.dl --examples programs/sg.examples \\
                         --candidates programs/sg.candidates

Exit status: 0, or 3 when no subset of the candidates fits the examples
(or the chosen rules do not reproduce them once run with the program).
"""

from __future__ import annotations

import argparse
import itertools
import sys

from tiny_datalog.containment import minimise
from tiny_datalog.core import (
    Atom, cli, Const, DatalogError, format_atom, Literal, parse,
    read_program, Rule, sort_key, validate, Var)
from tiny_datalog.diagnose import run
from tiny_datalog.foil import arities, NAMES, read_examples, report
from tiny_datalog.sat import solve  # noqa: F401 -- the loop's other half
from tiny_datalog.semiring import SemiringEngine, WhySemiring

TAG = "#rule"      # '#' starts a comment, so no program can name it


# ---------------------------------------------------------------------------
# Candidates
# ---------------------------------------------------------------------------

def _connected(head, body):
    """Does every body atom reach the head through shared variables?
    One that does not constrains nothing the head mentions."""
    reached = {a.name for a in head.args}
    left = list(body)
    while True:
        joined = [a for a in left if reached & {v.name for v in a.args}]
        if not joined:
            return not left
        for atom in joined:
            reached |= {v.name for v in atom.args}
            left.remove(atom)


def candidates(arity, target, max_body=2, extra=1):
    """Every rule for `target` with up to `max_body` body atoms over the
    predicates in `arity`, using the head's variables and `extra` more.
    Kept: safe rules, whose atoms all connect to the head, in one
    spelling each (renaming the extra variables gives the same rule),
    and minimal (lesson 16: a body with a redundant atom is the same
    query as a smaller body already in the list)."""
    n = arity[target]
    head = Atom(target, tuple(Var(v) for v in NAMES[:n]))
    spare = NAMES[n:n + extra]
    atoms = [Atom(pred, tuple(Var(v) for v in names))
             for pred in sorted(arity) if arity[pred]
             for names in itertools.permutations(NAMES[:n + extra],
                                                 arity[pred])]
    atoms = [a for a in atoms if a != head]

    def spelling(body, order):
        # variables as their position in NAMES, so that the spelling
        # kept is the one using the earliest spare variables
        rename = dict(zip(spare, order))
        return sorted((a.pred, [NAMES.index(rename.get(v.name, v.name))
                                for v in a.args]) for a in body)

    out = []
    for size in range(1, max_body + 1):
        for body in itertools.combinations(atoms, size):
            used = {v.name for a in body for v in a.args}
            if not {v.name for v in head.args} <= used \
                    or not _connected(head, body):
                continue
            if spelling(body, spare) != min(
                    spelling(body, p) for p in itertools.permutations(spare)):
                continue
            rule = Rule(head, tuple(Literal(a) for a in body))
            if len(minimise(rule)) == size:
                out.append(rule)
    return out


# ---------------------------------------------------------------------------
# Provenance over rules
# ---------------------------------------------------------------------------

class RuleProvenance(WhySemiring):
    """Lesson 8's why-provenance with rules for tokens.  Each candidate
    carries one extra body literal, `#rule(i)`, and that fact is the
    only kind with a token; every other fact is worth `one`.  A value
    is then the minimal sets of rules sufficient to derive a fact."""
    name = "rules"

    def fact_value(self, pred, tup, weight):
        return frozenset([frozenset(tup)]) if pred == TAG else self.one


class Synthesiser:
    """One problem: background facts, numbered candidate rules (from
    1), and examples of one target predicate."""

    def __init__(self, facts, rules, target, pos, neg, trace=False):
        self.facts, self.rules, self.target = facts, rules, target
        self.pos, self.neg, self.trace = pos, neg, trace
        self.clauses, self.runs, self.rounds = [], 0, 0

    def program(self, on):
        return self.facts + [self.rules[i - 1] for i in sorted(on)]

    def derived(self, on):
        """The target's tuples when the rules in `on` are run."""
        self.runs += 1
        return run(self.program(on)).rels.get(self.target, set())

    def why(self, on, tuples):
        """{tuple: its minimal deriving rule sets} under the rules `on`."""
        tagged = [Rule(Atom(TAG, (Const(i),)), ()) for i in sorted(on)]
        tagged += [Rule(r.head, r.body + (Literal(Atom(TAG, (Const(i),))),))
                   for i, r in enumerate(self.rules, 1) if i in on]
        self.runs += 1
        # no round budget: sets of rules are finite and only shrink
        # under absorption, so this always reaches a fixpoint, and a
        # long chain of facts needs as many rounds as it has links
        engine = SemiringEngine(self.facts + tagged,
                                RuleProvenance()).run(sys.maxsize)
        return {t: engine.value(self.target, t) for t in tuples}

    def why_not(self, on, tup):
        """Rules of which at least one must be on for `tup` to be
        derived: what is still off after switching on as many others as
        leave it missing.  Tried in halves (delta debugging), so a
        large batch of irrelevant rules costs one run, not one each."""
        on = set(on)

        def grow(batch):
            if tup not in self.derived(on | set(batch)):
                on.update(batch)
            elif len(batch) > 1:
                grow(batch[:len(batch) // 2])
                grow(batch[len(batch) // 2:])

        grow([i for i in range(1, len(self.rules) + 1) if i not in on])
        return [i for i in range(1, len(self.rules) + 1) if i not in on]

    def _say(self, text):
        if self.trace:
            print(text)

    def search(self):
        """The chosen rule numbers, or None if no subset fits."""
        name = lambda ids: ", ".join("r%d" % i for i in sorted(ids)) or "-"
        fact = lambda t: format_atom(self.target, t)
        while True:
            on = solve(self.clauses)
            if on is None:
                return None
            self.rounds += 1
            got = self.derived(on)
            wrong = sorted(got & self.neg, key=sort_key)
            missing = sorted(self.pos - got, key=sort_key)
            self._say("round %d: try {%s}: %d wrong, %d missing"
                      % (self.rounds, name(on), len(wrong), len(missing)))
            if not wrong and not missing:
                return self._prune(on)
            learned = []
            if wrong:
                for t, witnesses in self.why(on, wrong).items():
                    for w in sorted(witnesses, key=sorted):
                        clause = sorted(-i for i in w)
                        if clause not in learned:
                            learned.append(clause)
                            self._say("   wrong %s, derived by {%s}: forbid "
                                      "that set" % (fact(t), name(w)))
            if missing:
                clause = self.why_not(on, missing[0])
                self._say("   missing %s: require one of {%s}"
                          % (fact(missing[0]), name(clause)))
                learned.append(clause)
            self.clauses += learned

    def _prune(self, on):
        """A solution may carry rules it does not need: drop each one
        whose loss changes nothing the examples can see."""
        for i in sorted(on, reverse=True):
            got = self.derived(on - {i})
            if self.pos <= got and not got & self.neg:
                on = on - {i}
        return on


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Learn rules by choosing among candidates, guided "
                    "by why and why-not provenance (after ProSynth).")
    ap.add_argument("file", help="background facts (and rules)")
    ap.add_argument("--examples", required=True, metavar="FILE",
                    help="facts are positive examples, `:- fact.` negative; "
                         "with no negatives the world is closed")
    ap.add_argument("--candidates", metavar="FILE",
                    help="take the candidate rules from a file instead "
                         "of enumerating them")
    ap.add_argument("--max-body", type=int, default=2, metavar="N",
                    help="enumerate bodies of up to N atoms (default 2)")
    ap.add_argument("--vars", type=int, default=1, metavar="N",
                    help="variables a body may add to the head's (default 1)")
    ap.add_argument("-t", "--trace", action="store_true",
                    help="show every round and the constraint it taught")
    args = ap.parse_args(argv)

    clauses = parse(read_program(args.file))
    engine = run(clauses)
    target, pos, neg, closed = read_examples(read_program(args.examples),
                                             engine)
    # the background, already evaluated: whatever the program's own
    # rules derive is simply a fact as far as the candidates can tell
    facts = [Rule(Atom(p, tuple(Const(v) for v in t)), ())
             for p, tuples in sorted(engine.rels.items())
             for t in sorted(tuples, key=sort_key)]
    arity = arities({**engine.rels, target: pos})
    print("target %s/%d: %d positive examples, %d negative%s"
          % (target, arity[target], len(pos), len(neg),
             " (closed world)" if closed else ""))
    if args.candidates:
        rules = [c for c in parse(read_program(args.candidates)) if c.body]
        validate(facts + rules)
        if any(lit.negated for r in rules for lit in r.body):
            raise DatalogError("candidates must be positive rules: a "
                               "why-not constraint relies on monotonicity")
        print("%d candidate rules from %s" % (len(rules), args.candidates))
    else:
        rules = candidates(arity, target, args.max_body, args.vars)
        print("%d candidate rules: bodies of up to %d atom%s, %d extra "
              "variable%s" % (len(rules), args.max_body,
                              "" if args.max_body == 1 else "s", args.vars,
                              "" if args.vars == 1 else "s"))
    if args.trace:
        for i, rule in enumerate(rules, 1):
            print("   r%-3d %s" % (i, rule))
    job = Synthesiser(facts, rules, target, pos, neg, args.trace)
    chosen = job.search()
    print("%d rounds, %d constraints, %d evaluations"
          % (job.rounds, len(job.clauses), job.runs))
    if chosen is None:
        print("no subset of the candidates fits the examples: widen the "
              "candidates (--max-body, --vars, --candidates), or check "
              "the examples")
        return 3
    return 0 if report(clauses, [rules[i - 1] for i in sorted(chosen)],
                       target, pos, neg) else 3


if __name__ == "__main__":
    sys.exit(main())
