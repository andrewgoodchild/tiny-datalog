#!/usr/bin/env python3
"""
incremental.py — incremental maintenance of Datalog materialisations.

Evaluate once; then, as base facts arrive and depart, repair the derived
relations instead of recomputing them from scratch.

* Insertion is semi-naive evaluation *resumed*: the database is already a
  fixpoint of the old facts, so every genuinely new derivation must use at
  least one inserted fact — exactly the delta discipline the engine
  already runs.
* Deletion ships in two strategies, because the field did:
  - DRed (delete-and-rederive, Gupta–Mumick–Subrahmanian 1993): first
    over-delete everything that has *any* derivation through a deleted
    fact, then re-derive the survivors that still have support from what
    remains.
  - Backward/Forward (Motik–Nenov–Piro–Horrocks 2015, the algorithm in
    RDFox): compute the same affected set, but instead of tearing it
    down, check each fact by *backward chaining* for an alternative
    derivation before touching it.  Facts with independent support are
    never disturbed.  The search must be well-founded — a fact may not
    support itself through a cycle — which is the same reason counting
    derivations fails on recursion (lesson 7's diverging count semiring).

Both repair to exactly the recomputed state; they differ in where the
work goes.  DRed pays teardown-plus-rebuild in proportion to derivation
*redundancy*; B/F pays proof search in proportion to how hard survival
is to confirm.  Positive programs only — incrementalising negation is
exactly where the modern theory earns its keep.

Run `python3 incremental.py` for a demo: delete one edge from a graph
with an alternative route and watch DRed over-delete, then re-derive.

API
---
    inc = IncrementalEngine(program_text)
    inc.insert("edge(n2, n9).")   -> {"inserted": 1, "derived": 2}
    inc.delete("edge(n3, n4).")   -> {"deleted": 1, "over_deleted": 7,
                                      "rederived": 4, "net_removed": 3}
    inc.delete(..., strategy="bf")  # {"affected": 7, "confirmed": 4, ...}
    inc.rels                       # always the same as recomputing fresh
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict

from datalog import (DatalogError, Engine, Program, _aggregate_of,
                     _match, _sort_key, format_fact, parse, validate)


class IncrementalEngine:
    def __init__(self, text):
        clauses = parse(text)
        for r in clauses:
            if any(lit.negated for lit in r.body) or _aggregate_of(r.head):
                raise DatalogError(
                    "incremental maintenance supports positive, "
                    "aggregate-free programs only (negation and "
                    "aggregation are non-monotone; maintaining them is "
                    "where the modern theory earns its keep): %s" % r)
        self.program = Program(clauses)
        self.engine = Engine(self.program)
        self.engine.run()
        self.rels = self.engine.rels
        self.rules = self.program.rules
        self.base = {(c.head.pred, tuple(a.value for a in c.head.args))
                     for c in clauses if not c.body}

    # -- helpers ------------------------------------------------------------

    def _facts_of(self, clauses):
        """Validate incoming fact clauses against the loaded program.
        validate() (seeded with the program's arity map) enforces the
        same invariants Program enforces at load time — ground,
        function-free, arity-consistent — so the materialisation can
        never be corrupted through this door."""
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
        clauses = parse(facts_text)
        if any(c.retract for c in clauses):
            raise DatalogError(
                "insert() received a retraction — use delete() or apply()")
        return self._insert_facts(self._facts_of(clauses))

    def delete(self, facts_text, strategy="dred"):
        """Remove base facts (a trailing `~` is allowed but optional
        here); repair derived relations with DRed or Backward/Forward."""
        deleter = (self._bf_delete_facts if strategy == "bf"
                   else self._delete_facts)
        return deleter(self._facts_of(parse(facts_text)))

    def apply(self, script, strategy="dred"):
        """Apply a mixed update script in one call: plain facts insert,
        `fact~.` retracts.  Deletions run first, then insertions;
        returns the combined stats.

            inc.apply("edge(n3, n4)~.  edge(n2, n9).")
        """
        clauses = parse(script)
        stats = {}
        deletes = [c for c in clauses if c.retract]
        inserts = [c for c in clauses if not c.retract]
        if deletes:
            deleter = (self._bf_delete_facts if strategy == "bf"
                       else self._delete_facts)
            stats.update(deleter(self._facts_of(deletes)))
        if inserts:
            stats.update(self._insert_facts(self._facts_of(inserts)))
        return stats

    def _insert_facts(self, facts):
        delta = defaultdict(set)
        inserted = 0
        for pred, tup in facts:
            self.base.add((pred, tup))
            if tup not in self.rels[pred]:
                self.rels[pred].add(tup)
                delta[pred].add(tup)
                inserted += 1
        derived = self._propagate(delta)
        return {"inserted": inserted, "derived": len(derived)}

    def _delete_facts(self, facts):
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

    def _bf_delete_facts(self, facts):
        """Backward/Forward: forward-propagate the affected set against
        the intact database, then decide each affected fact by backward
        proof search before removing anything.  `blocked` carries the
        current proof path, so support is well-founded by construction —
        a fact cannot survive by deriving itself around a cycle."""
        for f in facts:
            if f not in self.base:
                raise DatalogError("can only delete base facts; %s is "
                                   "not one" % format_fact(*f))
        self.base -= set(facts)
        frontier, affected = defaultdict(set), set()
        for pred, tup in facts:
            if tup in self.rels.get(pred, ()):
                frontier[pred].add(tup)
                affected.add((pred, tup))
        while frontier:
            nxt = defaultdict(set)
            for pred, tup in self._delta_fires(frontier):
                if tup in self.rels[pred] and (pred, tup) not in affected:
                    affected.add((pred, tup))
                    nxt[pred].add(tup)
            frontier = nxt

        by_head = defaultdict(list)
        for r in self.rules:
            by_head[r.head.pred].append(r)
        proven, checks = {}, [0]

        def usable(f, blocked):
            if f in blocked:
                return False
            if f not in affected or f in self.base:
                return True
            if f in proven:
                return proven[f]
            return prove(f, blocked | {f})

        def prove(f, blocked):
            # only successes are cached: failure under a nonempty proof
            # path may succeed by another route; False is recorded only
            # after a top-level search exhausts them all
            checks[0] += 1
            pred, tup = f
            for rule in by_head[pred]:
                subst = _match(rule.head.args, tup, {})
                if subst is not None and solve(rule.body, 0, subst, blocked):
                    proven[f] = True
                    return True
            return False

        def solve(body, i, subst, blocked):
            if i == len(body):
                return True
            atom = body[i].atom
            for tup in sorted(self.rels.get(atom.pred, ()), key=_sort_key):
                ext = _match(atom.args, tup, subst)
                if (ext is not None and usable((atom.pred, tup), blocked)
                        and solve(body, i + 1, ext, blocked)):
                    return True
            return False

        removed = 0
        order = sorted(affected, key=lambda f: (f[0], _sort_key(f[1])))
        for f in order:
            alive = (f in self.base or proven.get(f) is True
                     or (f not in proven and prove(f, {f})))
            if alive:
                continue
            proven[f] = False
            self.rels[f[0]].discard(f[1])
            removed += 1
        for pred in [p for p, ts in self.rels.items() if not ts]:
            del self.rels[pred]
        return {"deleted": len(facts), "affected": len(affected),
                "confirmed": len(affected) - removed, "removed": removed,
                "backward_checks": checks[0]}

    def total_facts(self):
        return sum(len(ts) for ts in self.rels.values())


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

_DEMO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "programs", "dred-graph.dl")


def _demo():
    with open(_DEMO_FILE) as fh:
        text = fh.read()
    t0 = time.perf_counter()
    inc = IncrementalEngine(text)
    print("Initial: %d path facts, materialised in %.3fs"
          % (len(inc.rels["path"]), time.perf_counter() - t0))
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


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="incremental.py",
        description="Materialise a program, then repair it under updates "
                    "instead of recomputing.  Update scripts mix inserts "
                    "(plain facts) and retractions (`fact~.`).")
    ap.add_argument("file", nargs="?",
                    help="program to materialise; omit to run the "
                         "built-in DRed demo")
    ap.add_argument("-u", "--update", action="append", default=[],
                    metavar="SCRIPT",
                    help="update script applied in order, e.g. "
                         "'edge(n3, n4)~. edge(n2, n9).' (repeatable)")
    ap.add_argument("-p", "--print", dest="show", action="store_true",
                    help="print derived relations after the updates")
    ap.add_argument("--strategy", choices=("dred", "bf"), default="dred",
                    help="deletion strategy: DRed (default) or "
                         "Backward/Forward")
    args = ap.parse_args(argv)

    if not args.file:
        return _demo()
    try:
        with open(args.file) as fh:
            inc = IncrementalEngine(fh.read())
        print("materialised: %d facts" % inc.total_facts())
        for script in args.update:
            t0 = time.perf_counter()
            stats = inc.apply(script, args.strategy)
            elapsed = time.perf_counter() - t0
            print("%s\n  -> %r in %.3fs" % (script.strip(), stats, elapsed))
        if args.update:
            t0 = time.perf_counter()
            fresh = Engine(Program(parse(open(args.file).read())))
            fresh.run()
            print("  (a from-scratch rebuild of this program: %.3fs)"
                  % (time.perf_counter() - t0))
    except DatalogError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    if args.show:
        from datalog import _sort_key, format_fact
        print()
        for pred in sorted(inc.program.idb):
            for tup in sorted(inc.rels.get(pred, ()), key=_sort_key):
                print(format_fact(pred, tup))
    return 0


if __name__ == "__main__":
    sys.exit(main())
