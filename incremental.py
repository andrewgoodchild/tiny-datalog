#!/usr/bin/env python3
"""
incremental.py — incremental maintenance of Datalog materialisations.

Evaluate once; then, as base facts arrive and depart, repair the derived
relations instead of recomputing them from scratch.

* Insertion is semi-naive evaluation *resumed*: the database is already a
  fixpoint of the old facts, so every genuinely new derivation must use at
  least one inserted fact — exactly the delta discipline the engine
  already runs.
* Deletion is DRed (delete-and-rederive, Gupta–Mumick–Subrahmanian 1993):
  first over-delete everything that has *any* derivation through a
  deleted fact, then re-derive the survivors that still have support from
  what remains.

This two-phase dance is the teaching-sized ancestor of modern incremental
view maintenance (Differential Dataflow, DBSP).  Positive programs only —
incrementalising negation is exactly where the modern theory earns its
keep.

Run `python3 incremental.py` for a demo: delete one edge from a graph
with an alternative route and watch DRed over-delete, then re-derive.

API
---
    inc = IncrementalEngine(program_text)
    inc.insert("edge(n2, n9).")   -> {"inserted": 1, "derived": 2}
    inc.delete("edge(n3, n4).")   -> {"deleted": 1, "over_deleted": 7,
                                      "rederived": 4, "net_removed": 3}
    inc.rels                       # always the same as recomputing fresh
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict

from datalog import (DatalogError, Engine, Program, format_fact, parse,
                     validate)


class IncrementalEngine:
    def __init__(self, text):
        clauses = parse(text)
        for r in clauses:
            if any(lit.negated for lit in r.body):
                raise DatalogError(
                    "incremental maintenance supports positive programs "
                    "only (negated literal in: %s)" % r)
        self.program = Program(clauses)
        self.engine = Engine(self.program)
        self.engine.run()
        self.rels = self.engine.rels
        self.rules = self.program.rules
        self.base = {(c.head.pred, tuple(a.value for a in c.head.args))
                     for c in clauses if not c.body}

    # -- helpers ------------------------------------------------------------

    def _parse_facts(self, text):
        """Parse and validate incoming facts against the loaded program.
        validate() (seeded with the program's arity map) enforces the
        same invariants Program enforces at load time — ground,
        function-free, arity-consistent — so the materialisation can
        never be corrupted through this door."""
        clauses = parse(text)
        for c in clauses:
            if c.body:
                raise DatalogError("expected facts only, got a rule: %s" % c)
            if c.weight is not None:
                raise DatalogError(
                    "weights are not supported by the incremental "
                    "engine: %s" % c)
        validate(clauses, self.program.arity)
        return [(c.head.pred, tuple(a.value for a in c.head.args))
                for c in clauses]

    def _delta_fires(self, delta):
        """One round of delta-joins: yield every (head_pred, tuple) some
        rule derives using at least one fact from `delta`.  This is the
        engine's own semi-naive discipline exposed as a generator —
        insert() aims it at what's new, delete() aims it at what's
        dying.  Same mechanism, two directions."""
        for rule in self.rules:
            for i, lit in enumerate(rule.body):
                if not delta.get(lit.atom.pred):
                    continue
                for tup in self.engine._eval_rule(rule, delta_occ=i,
                                                  delta=delta):
                    yield rule.head.pred, tup

    def _propagate(self, delta):
        """Semi-naive continuation: `delta` maps pred -> tuples already
        added to rels.  Returns the set of additionally derived facts."""
        derived = set()
        while delta:
            new_delta = defaultdict(set)
            for pred, tup in self._delta_fires(delta):
                if tup not in self.rels[pred]:
                    new_delta[pred].add(tup)
            for pred, tups in new_delta.items():
                self.rels[pred] |= tups
                derived |= {(pred, t) for t in tups}
            delta = new_delta
        return derived

    # -- the API ------------------------------------------------------------

    def insert(self, facts_text):
        """Add base facts; repair derived relations by delta propagation."""
        delta = defaultdict(set)
        inserted = 0
        for pred, tup in self._parse_facts(facts_text):
            self.base.add((pred, tup))
            if tup not in self.rels[pred]:
                self.rels[pred].add(tup)
                delta[pred].add(tup)
                inserted += 1
        derived = self._propagate(delta)
        return {"inserted": inserted, "derived": len(derived)}

    def delete(self, facts_text):
        """Remove base facts; repair derived relations with DRed."""
        facts = self._parse_facts(facts_text)
        for f in facts:
            if f not in self.base:
                raise DatalogError(
                    "can only delete base facts; %s is not one"
                    % format_fact(*f))

        # Phase 1: over-delete.  A fact is a candidate if any derivation
        # of it passes through a deleted fact — computed with delta-joins
        # against the *pre-deletion* database.
        frontier = defaultdict(set)
        candidates = set()
        for pred, tup in facts:
            self.base.discard((pred, tup))
            if tup in self.rels[pred]:
                frontier[pred].add(tup)
                candidates.add((pred, tup))
        while frontier:
            nxt = defaultdict(set)
            for pred, tup in self._delta_fires(frontier):
                if tup in self.rels[pred] and (pred, tup) not in candidates:
                    candidates.add((pred, tup))
                    nxt[pred].add(tup)
            frontier = nxt

        for pred, tup in candidates:
            self.rels[pred].discard(tup)

        # Explicit base facts swept up as collateral survive.
        seed = defaultdict(set)
        for pred, tup in candidates:
            if (pred, tup) in self.base:
                self.rels[pred].add(tup)
                seed[pred].add(tup)

        # Phase 2: re-derive candidates that still have a derivation from
        # the surviving facts, then propagate.  Only rules that can head
        # a candidate need re-evaluating.
        cand_preds = {p for p, _t in candidates}
        for rule in self.rules:
            if rule.head.pred not in cand_preds:
                continue
            for tup in self.engine._eval_rule(rule):
                f = (rule.head.pred, tup)
                if f in candidates and tup not in self.rels[rule.head.pred]:
                    self.rels[rule.head.pred].add(tup)
                    seed[rule.head.pred].add(tup)
        self._propagate(seed)

        rederived = sum(1 for pred, tup in candidates
                        if tup in self.rels[pred])
        # keep the "same as recomputing fresh" invariant exact: a fresh
        # engine has no entry for a predicate with no facts at all
        for pred in [p for p, ts in self.rels.items() if not ts]:
            del self.rels[pred]
        return {"deleted": len(facts),
                "over_deleted": len(candidates),
                "rederived": rederived,
                "net_removed": len(candidates) - rederived}

    def total_facts(self):
        return sum(len(ts) for ts in self.rels.values())


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

_DEMO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "programs", "08-dred-graph.dl")


def _demo():
    with open(_DEMO_FILE) as fh:
        text = fh.read()
    inc = IncrementalEngine(text)
    print("Initial: %d path facts" % len(inc.rels["path"]))
    print()
    print('delete("edge(n3, n4).")   — n2\'s shortcut keeps most paths alive:')
    stats = inc.delete("edge(n3, n4).")
    print("  %r" % stats)
    print("  over-deleted %d candidates, re-derived %d — only %d facts "
          "actually died" % (stats["over_deleted"], stats["rederived"],
                             stats["net_removed"]))
    print("  now: %d path facts" % len(inc.rels["path"]))
    print()
    print('insert("edge(n3, n4).")   — put it back:')
    stats = inc.insert("edge(n3, n4).")
    print("  %r" % stats)
    print("  now: %d path facts" % len(inc.rels["path"]))
    # sanity: identical to computing from scratch
    fresh = Engine(Program(parse(text)))
    fresh.run()
    assert inc.rels["path"] == fresh.rels["path"]
    print()
    print("Repaired state verified equal to a from-scratch recomputation.")


if __name__ == "__main__":
    sys.exit(_demo())
