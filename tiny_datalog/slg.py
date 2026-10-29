#!/usr/bin/env python3
"""
slg.py — SLG resolution: tabled top-down evaluation that computes the
well-founded semantics.  (Lesson 15, the second half.)

tabling.py answers queries top-down with a table per subgoal, but it
pays for its size twice: it re-solves every table in rounds until none
grows, and it refuses negation through recursion.  SLG resolution
(Chen & Warren 1996, the engine inside XSB Prolog) fixes both with the
three ideas Lesson 15 names:

1. **Suspend and resume.**  A call to a subgoal that already has a
   table does not re-derive anything.  It registers as a *consumer* of
   that table — the rest of its rule body, waiting — and every answer
   the table gains is pushed to every consumer exactly once.  Python
   generators cannot be copied or resumed twice, so a suspended call is
   plain data: (the calling subgoal, its rule head, the body literals
   still to prove, the substitution so far, the delays so far).

2. **Detect completion.**  When there is no work left, the incomplete
   tables and the calls between them form a graph.  A group of tables
   with no call out to another incomplete table can never grow again:
   complete it.  That is what lets `not q` be decided without strata —
   wait until q's group completes, then look.  The groups are found the
   way XSB finds them, on a *completion stack*: tables in the order
   they were created, the newest on top.  Scanning down from the top,
   the first point below which nothing calls is the bottom of a group
   that can complete.  That group may hold several strongly connected
   components (XSB calls it an approximate SCC); only when it is stuck
   on negation does the precise answer matter, and only then does
   Tarjan's algorithm run, on that group alone.  A table of facts never
   goes on the stack at all: it calls nothing, so it is complete the
   moment it is filled.

3. **Delay, then simplify.**  A component can be stuck: every remaining
   call inside it is a `not` on a table of the same component, so each
   waits for the other to complete (win(a) needs not win(b), which needs
   not win(a)).  SLG *delays* such literals — carries on as if they
   succeeded, recording them on the answer as a condition.  Once the
   component completes, conditions are *simplified* against the
   finished tables: a literal now known true is struck out, a literal
   known false kills its condition, and answers with no condition left
   are true.  One more step, *answer completion*, removes answers that
   only support each other through a positive loop.  Whatever is still
   conditional at the end is **undefined**.

The result is the well-founded model of Lesson 5 (semantics.py),
computed top-down and only for the subgoals the query reaches.  The
test suite checks exactly that, on random unstratified programs.

What this leaves out, compared with XSB: aggregation, integrity
constraints, and the machine-level engineering (an abstract machine,
answer tries, scheduling one subgoal's work locally).  The two
algorithmic economies are here: completion by stack, and conditions
kept minimal (an answer true under A needs no second condition A and B).

CLI
---
    python3 slg.py programs/win.dl -q 'win(X)'
    python3 slg.py programs/left-recursive.dl -q 'ancestor(abe, X)' -t
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict, deque

from tiny_datalog.core import (
    _tarjan, check_query_atom, cli, Const, format_atom, format_fact,
    match, parse, parse_goal, read_program, sort_key, holds, is_comparison)
from tiny_datalog.tabling import call_pattern, head_seed, index_clauses

UNCONDITIONAL = frozenset()   # the empty condition: the answer is true


class SLGEngine:
    """SLG resolution for function-free programs, any negation.

    After query(), `tables` maps a subgoal (pred, pattern) — pattern has
    a constant per bound argument and None per free one — to
    {answer tuple: set of conditions}.  A condition is a frozenset of
    delayed literals; the empty one means the answer is true, and an
    answer with only non-empty conditions is undefined.  A delayed
    literal is ("+", subgoal, answer) — "that answer of that table" —
    or ("-", subgoal) for `not` of a ground subgoal.  `stats` counts
    the work done."""

    def __init__(self, clauses):
        # the same front end as tabling.py: positive literals first, so
        # by the time a negation is reached its subgoal is ground
        self.arity, self.by_pred = index_clauses(clauses, "SLG")
        self.root = None                   # the last query's subgoal
        self._reset()

    def _reset(self):
        self.tables = {}
        self.order = {}                    # subgoal -> creation number
        self.complete = set()
        self.stack = []                    # incomplete subgoals, oldest first
        self.consumers = defaultdict(list) # subgoal -> waiting `p(...)`
        self.waiting = defaultdict(list)   # subgoal -> waiting `not p(...)`
        self.calls = defaultdict(set)      # subgoal -> subgoals it called
        self.work = deque()                # frames ready to run
        self.stats = Counter()

    # -- subgoals ------------------------------------------------------------

    def _call(self, caller, key):
        """Note that `caller` depends on `key`; on a first call, make
        its table and schedule its clauses (program clause resolution)."""
        if caller is not None:
            self.calls[caller].add(key)
        if key in self.tables:
            return
        self.tables[key] = {}
        self.order[key] = len(self.order)
        pred, pattern = key
        clauses = self.by_pred.get((pred, len(pattern)), ())
        facts_only = not any(body for _head, body in clauses)
        if not facts_only:
            self.stack.append(key)
        for head, body in clauses:
            seed = head_seed(head, pattern)
            if seed is None:
                continue
            self.stats["clause resolutions"] += 1
            if facts_only:
                self._answer(key, tuple(a.value for a in head.args),
                             UNCONDITIONAL)
            else:
                self.work.append((key, head, body, seed, UNCONDITIONAL))
        if facts_only:
            # a table of facts calls nothing, so it is complete the
            # moment it is filled: `not` on it never waits
            self.complete.add(key)

    # -- running frames ------------------------------------------------------

    def _step(self, frame):
        """Prove the next literal of a frame: (subgoal, head, remaining
        body, substitution, condition)."""
        key, head, body, subst, cond = frame
        if not body:
            self._answer(key, tuple(a.value if isinstance(a, Const)
                                    else subst[a.name] for a in head.args),
                         cond)
            return
        lit, rest = body[0], body[1:]
        if is_comparison(lit):          # a test, never a subgoal
            if holds(lit.atom, subst):
                self.work.append((key, head, rest, subst, cond))
            return
        callee = (lit.atom.pred, call_pattern(lit.atom, subst))
        self._call(key, callee)
        waiter = (key, head, rest, subst, cond, lit)
        if lit.negated:
            if callee in self.complete:
                self._negative_return(waiter, callee)
            elif not self._proved(callee):  # else `not` fails at once
                self.waiting[callee].append(waiter)
            return
        # suspend as a consumer, then catch up on the answers so far
        self.consumers[callee].append(waiter)
        for tup in list(self.tables[callee]):
            self._positive_return(waiter, callee, tup)

    def _proved(self, key):
        """Whether a table already holds a true answer.  For a ground
        subgoal that settles `not` early: more answers cannot undo it."""
        return any(UNCONDITIONAL in c for c in self.tables[key].values())

    def _answer(self, key, tup, cond):
        """Record an answer; a new tuple goes to every consumer."""
        answers = self.tables[key]
        conds = answers.get(tup)
        if conds is not None:
            # keep the conditions minimal: under A, "A and B" adds
            # nothing (and the empty condition, true, absorbs them all)
            if any(c <= cond for c in conds):
                self.stats["conditions absorbed"] += 1
                return
            conds.difference_update({c for c in conds if cond <= c})
            conds.add(cond)
            return
        answers[tup] = {cond}
        for waiter in self.consumers[key]:
            self._positive_return(waiter, key, tup)

    def _positive_return(self, waiter, key, tup):
        """Resume a consumer with one answer.  A conditional answer is
        returned once, as a delayed reference to itself; if it later
        turns out true or false, simplification settles the reference."""
        caller, head, rest, subst, cond, lit = waiter
        s = match(lit.atom.args, tup, subst)
        if s is None:
            return
        self.stats["answers returned"] += 1
        if UNCONDITIONAL not in self.tables[key][tup]:
            cond = cond | {("+", key, tup)}
        self.work.append((caller, head, rest, s, cond))

    def _negative_return(self, waiter, key):
        """Resume a `not` on a completed (and simplified) table."""
        caller, head, rest, subst, cond, _lit = waiter
        value = self._value(("-", key))
        if value is False:
            return
        if value is None:                # undefined: carry it along
            cond = cond | {("-", key)}
        self.work.append((caller, head, rest, subst, cond))

    # -- the scheduler -------------------------------------------------------

    def query(self, atom):
        """Answers to `atom` under the well-founded semantics, as
        (true, undefined): two sets of tuples.  Every other ground
        instance is false."""
        check_query_atom(atom, self.arity)
        self._reset()
        self.root = root = (atom.pred, call_pattern(atom, {}))
        self._call(None, root)
        self._evaluate()
        true, undefined = set(), set()
        for tup, conds in self.tables[root].items():
            if match(atom.args, tup, {}) is not None:
                (true if UNCONDITIONAL in conds else undefined).add(tup)
        return true, undefined

    def _evaluate(self):
        """Run frames until none are left, then complete the group of
        tables on top of the completion stack, or delay the negations it
        is stuck on; repeat until every table is complete."""
        while True:
            while self.work:
                self.stats["steps"] += 1
                self._step(self.work.popleft())
            if not self.stack:
                return
            group = self._closed_segment()
            if not any(w[0] in group for k in group
                       for w in self.waiting.get(k, ())):
                self._complete(group)   # the common case: no Tarjan
                continue
            # stuck on negation inside the group.  Delaying all of it
            # would be sound but blunt; find its bottom SCC and settle
            # that alone, so a `not` that one completion would decide is
            # decided, not delayed
            scc = self._bottom_component(group)
            stuck = {}
            for k in sorted(scc, key=self.order.get):
                waiting = self.waiting.get(k, ())
                inside = [w for w in waiting if w[0] in scc]
                if inside:
                    stuck[k] = inside
                    self.waiting[k] = [w for w in waiting if w[0] not in scc]
            if not stuck:
                self._complete(scc)
                continue
            # every `not` here waits on its own component: delay
            for k, waiters in stuck.items():
                if self._proved(k):     # true since they suspended
                    continue
                for caller, head, rest, subst, cond, _lit in waiters:
                    self.stats["delays"] += 1
                    self.work.append(
                        (caller, head, rest, subst, cond | {("-", k)}))

    def _closed_segment(self):
        """The smallest top segment of the completion stack that calls
        no incomplete table below it.  The stack is in creation order,
        so "below the segment" is "older than its oldest member": scan
        down from the top, tracking the oldest incomplete table called
        so far, and stop where it is no older than the table reached.
        Only the segment is scanned, and it is about to complete."""
        oldest = len(self.order)
        for i in range(len(self.stack) - 1, -1, -1):
            key = self.stack[i]
            # forget calls to finished tables: they never matter again
            calls = self.calls[key] = {
                v for v in self.calls[key] if v not in self.complete}
            for v in calls:
                oldest = min(oldest, self.order[v])
            if oldest >= self.order[key]:
                return set(self.stack[i:])
        raise AssertionError("the oldest table calls nothing older")

    def _bottom_component(self, group):
        """An SCC of `group` with no call out to the rest of it.
        Tarjan's algorithm emits a component only after every component
        it can reach, so its first one (id 0) is such a bottom."""
        # number the subgoals: patterns mix None, strings and numbers,
        # which do not sort against each other
        n = self.order
        edges = [(n[u], n[v], False) for u in group
                 for v in self.calls[u] if v in group]
        scc = _tarjan([n[k] for k in group], edges)
        return {k for k in group if scc[n[k]] == 0}

    def _complete(self, scc):
        """Mark a group complete, settle its conditional answers, then
        resume the negations waiting on it from above."""
        self.stats["completions"] += 1
        self.complete |= scc
        if set(self.stack[-len(scc):]) == scc:     # the usual case: the top
            del self.stack[-len(scc):]
        else:
            self.stack = [k for k in self.stack if k not in scc]
        self._simplify(scc)
        for k in sorted(scc, key=self.order.get):
            self.consumers.pop(k, None)      # these tables cannot grow
            self.calls.pop(k, None)          # ...nor be stuck on a call
            for waiter in self.waiting.pop(k, ()):
                self._negative_return(waiter, k)

    # -- simplification ------------------------------------------------------

    def _value(self, lit):
        """A delayed literal against completed tables: True, False, or
        None while it is still undecided."""
        if lit[0] == "+":
            _sign, key, tup = lit
            conds = self.tables[key].get(tup)
            if not conds:
                return False
            return True if UNCONDITIONAL in conds else None
        _sign, key = lit
        if not self.tables[key]:
            return True
        return False if self._proved(key) else None

    def _simplify(self, scc):
        """Settle a just-completed component's conditions.  Everything
        a condition mentions is complete now — this component or one
        below it, already settled — so each literal is True, False, or
        undecided.  Strike out the true ones, drop conditions with a
        false one, and repeat, interleaved with answer completion,
        until nothing changes."""
        changed = True
        while changed:
            changed = False
            for key in sorted(scc, key=self.order.get):
                answers = self.tables[key]
                for tup in list(answers):
                    conds = answers[tup]
                    if conds == {UNCONDITIONAL}:
                        continue
                    settled = set()
                    for cond in conds:
                        values = {lit: self._value(lit) for lit in cond}
                        if False not in values.values():
                            settled.add(frozenset(
                                lit for lit in cond if values[lit] is None))
                    # minimal again: settling can make one condition a
                    # subset of another (and the empty one absorbs all)
                    settled = {c for c in settled
                               if not any(d < c for d in settled)}
                    if settled != conds:
                        changed = True
                        self.stats["simplifications"] += 1
                        if settled:
                            answers[tup] = settled
                        else:
                            del answers[tup]
            if not changed:
                changed = self._drop_unfounded(scc)

    def _drop_unfounded(self, scc):
        """Answer completion: an answer of this component is supported
        if some condition of it rests, positively, only on supported
        answers of this component (negated and lower-component literals
        are undefined by now, and support nothing false).  Unsupported
        answers form an unfounded set — they hold each other up in a
        positive loop and nothing else holds them — so they are false.
        Returns whether any were dropped."""
        supported = set()
        grew = True
        while grew:
            grew = False
            for key in scc:
                for tup, conds in self.tables[key].items():
                    if (key, tup) in supported:
                        continue
                    if any(all(lit[0] == "-" or lit[1] not in scc
                               or (lit[1], lit[2]) in supported
                               for lit in cond) for cond in conds):
                        supported.add((key, tup))
                        grew = True
        dropped = False
        for key in scc:
            for tup in list(self.tables[key]):
                if (key, tup) not in supported:
                    del self.tables[key][tup]
                    self.stats["unfounded answers"] += 1
                    dropped = True
        return dropped


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def format_literal(lit):
    if lit[0] == "+":
        return format_atom(lit[1][0], lit[2])
    return "not " + format_atom(*lit[1])


def _plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="SLG resolution: tabled top-down evaluation under the "
                    "well-founded semantics — negation through recursion "
                    "included, with undefined answers named as such.")
    ap.add_argument("file", help="Datalog program (.dl)")
    ap.add_argument("-q", "--query", action="append", default=[],
                    metavar="ATOM", help="goal to solve (repeatable)")
    ap.add_argument("-t", "--tables", action="store_true",
                    help="also print every table and the work counters")
    args = ap.parse_args(argv)

    engine = SLGEngine(parse(read_program(args.file)))
    for q in args.query:
        atom = parse_goal(q)
        true, undefined = engine.query(atom)
        root = engine.tables[engine.root]
        print("?- %s   [SLG]" % atom)
        for tup in sorted(true, key=sort_key):
            print("   " + format_fact(atom.pred, tup))
        for tup in sorted(undefined, key=sort_key):
            # the residual conditions are the reason it is undefined
            reasons = sorted(", ".join(sorted(map(format_literal, c)))
                             for c in root[tup])
            print("   %s   undefined: if %s"
                  % (format_fact(atom.pred, tup), "; or if ".join(reasons)))
        print("   (%d true, %d undefined; %s, %s, %s)"
              % (len(true), len(undefined),
                 _plural(len(engine.tables), "subgoal table"),
                 _plural(engine.stats["completions"], "completion"),
                 _plural(engine.stats["delays"], "delay")))
        if args.tables:
            for (pred, pattern), answers in sorted(
                    engine.tables.items(),
                    key=lambda kv: (kv[0][0], str(kv[0][1]))):
                shown = ", ".join("_" if v is None else str(v)
                                  for v in pattern)
                n_true = sum(UNCONDITIONAL in c for c in answers.values())
                print("   table %s(%s): %d true, %d undefined"
                      % (pred, shown, n_true, len(answers) - n_true))
            print("   work: " + ", ".join(
                "%s %d" % (k, v) for k, v in sorted(engine.stats.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
