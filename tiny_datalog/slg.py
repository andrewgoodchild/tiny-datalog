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

2. **Detect completion.**  The incomplete tables and the calls between
   them form a graph.  A group of tables with no work left and no call
   out to another incomplete table can never grow again: complete it.  That is what lets `not q` be decided without strata —
   wait until q's group completes, then look.  The groups are found the
   way XSB finds them, on a *completion stack*: tables in the order
   they were created, the newest on top.  Scanning down from the top,
   the first point below which nothing calls is the bottom of a group
   that can complete.  That group may hold several strongly connected
   components (XSB calls it an approximate SCC); only when it is stuck
   on negation does the precise answer matter, and only then does
   Tarjan's algorithm run, on that group alone.  Scheduling is *local*,
   as in XSB: the newest table's work runs first, and a group is
   completed the moment its own work runs out, not when all work has.
   A table of facts never goes on the stack at all: it calls nothing,
   so it is complete the moment it is filled.

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

Aggregation is tabled too: tabling.py splits each aggregate rule so
its body has a table of its own, folded once that table is complete
(a cycle through an aggregate is refused, as is folding undefined
answers).  `subsumptive=True` (CLI `-s`) answers a positive call from
a more general table, complete or still growing, instead of starting
a new one; the call reads, and waits on, only its own slice of it.

Tables survive a change to the facts (apply(), tabling.TableSpace).
What this leaves out, compared with XSB: rebuilding a changed table
lazily, and the machine (an abstract machine, answer tries; the
indexes here are built per pattern asked for).  The algorithmic economies are
here: completion by stack, local scheduling, and conditions kept
minimal (an answer true under A needs no second condition A and B).

CLI
---
    python3 slg.py programs/win.dl -q 'win(X)'
    python3 slg.py programs/left-recursive.dl -q 'ancestor(abe, X)' -t
    python3 slg.py programs/from-start.dl -q 'from_start(Y)' -s

Integrity constraints are checked after the queries; one whose body
is true exits 3, and one whose body is only undefined is named.
"""

from __future__ import annotations

import argparse
import heapq
import sys
from collections import Counter, defaultdict, deque
from itertools import chain, count

from tiny_datalog.core import (
    _tarjan, check_query_atom, cli, Const, DatalogError, format_atom,
    format_fact, match, parse, read_program, sort_key, holds,
    is_comparison)
from tiny_datalog.datalog import _print_violations
from tiny_datalog.tabling import (
    TableSpace, add_steps, call_pattern, constraint_goals,
    counterexamples, fold_answers, free_positions, head_seed,
    index_clauses,
    run_steps, subsuming)

UNCONDITIONAL = frozenset()   # the empty condition: the answer is true


class SLGEngine(TableSpace):
    """SLG resolution for function-free programs, any negation.

    After query(), `tables` maps a subgoal (pred, pattern) — pattern has
    a constant per bound argument and None per free one — to
    {answer tuple: set of conditions}.  A condition is a frozenset of
    delayed literals; the empty one means the answer is true, and an
    answer with only non-empty conditions is undefined.  A delayed
    literal is ("+", subgoal, answer) — "that answer of that table" —
    or ("-", subgoal) for `not` of a ground subgoal.  `stats` counts
    the work done.  With subsumptive=True, a positive call answered from
    a more general table gets no table of its own."""

    def __init__(self, clauses, subsumptive=False):
        # the same front end as tabling.py: positive literals first, so
        # by the time a negation is reached its subgoal is ground; each
        # integrity constraint becomes a query
        clauses, self.goals = constraint_goals(clauses)
        self.arity, self.by_pred, self.sources = index_clauses(clauses)
        self.subsumptive = subsumptive
        self.root = None                   # the last query's subgoal
        self._reset()

    def _reset(self):
        self.tables = {}
        self.callers = defaultdict(set)    # subgoal -> subgoals it serves
        self.order = {}                    # subgoal -> creation number
        self.ids = count()                 # ...handed out from here
        self.complete = set()
        # pred -> free_positions -> patterns with a table: what -s reads
        self.shapes = defaultdict(lambda: defaultdict(set))
        self.indexes = {}                  # (general, positions) -> index
        self.indexed = defaultdict(set)    # general -> positions indexed
        self.sliced = defaultdict(lambda: defaultdict(list))
                                           # general -> (positions,
                                           # values) -> waiting calls
        self.stack = []                    # incomplete subgoals, oldest first
        self.consumers = defaultdict(list) # subgoal -> waiting `p(...)`
        self.waiting = defaultdict(list)   # subgoal -> waiting `not p(...)`
        self.folds = defaultdict(list)     # subgoal -> aggregates over it
        self.calls = defaultdict(set)      # subgoal -> subgoals it called
        self.work = defaultdict(deque)     # subgoal -> its frames to run
        self.ready = []                    # heap: newest subgoal with work
        self.stats = Counter()

    # -- subgoals ------------------------------------------------------------

    def _call(self, caller, key, subsume=False):
        """Note that `caller` depends on `key`; on a first call, make
        its table and schedule its clauses (program clause resolution).
        Returns the subgoal whose table answers the call: key's own, or
        with `subsume`, a more general one."""
        general = (key not in self.tables and subsume and self.subsumptive
                   and subsuming(self.shapes, key))
        if general:
            self.stats["subsumed calls"] += 1
            # if the general table is still growing, the call becomes
            # one of its consumers, as a recursive call does, and the
            # edges below make them complete together
            key = general
        if caller is not None:
            self.callers[key].add(caller)
            self.calls[caller].add(key)
        if key in self.tables:
            return key
        self.tables[key] = {}
        self.order[key] = next(self.ids)
        pred, pattern = key
        self.shapes[pred][free_positions(pattern)].add(pattern)
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
                self._push((key, head, body, seed, UNCONDITIONAL))
        if facts_only:
            # a table of facts calls nothing, so it is complete the
            # moment it is filled: `not` on it never waits
            self.complete.add(key)
        return key

    def _forget(self, keys):
        """apply()'s half: forget thrown-away tables, here and in what
        subsumption reads."""
        super()._forget(keys)
        for k in keys:
            for at in self.indexed.pop(k, ()):
                del self.indexes[k, at]
            self.shapes[k[0]][free_positions(k[1])].discard(k[1])

    def _restore(self, key, answers):
        super()._restore(key, answers)
        self.order[key] = next(self.ids)
        self.shapes[key[0]][free_positions(key[1])].add(key[1])

    def _push(self, frame):
        """Queue a frame on its own subgoal; the scheduler runs the
        newest subgoal's frames first."""
        queue = self.work[frame[0]]
        if not queue:
            heapq.heappush(self.ready, (-self.order[frame[0]], frame[0]))
        queue.append(frame)

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
                self._push((key, head, rest, subst, cond))
            return
        wanted = (lit.atom.pred, call_pattern(lit.atom, subst))
        callee = self._call(key, wanted, subsume=not lit.negated)
        if lit.atom.pred in self.sources:
            # an aggregate's body table, split off by index_clauses: fold
            # it once, when it is complete
            if callee in self.complete:
                self._fold(key, lit.atom, callee)
            else:
                self.folds[callee].append((key, lit.atom))
            return
        waiter = (key, head, rest, subst, cond, lit)
        if lit.negated:
            if callee in self.complete:
                self._negative_return(waiter, callee)
            elif not self._proved(callee):  # else `not` fails at once
                self.waiting[callee].append(waiter)
            return
        # suspend as a consumer (a complete table has nothing more to
        # send), then catch up on the answers so far
        if callee != wanted:            # served by a general table
            answers = self._slice(callee, wanted[1], waiter)
        else:
            if callee not in self.complete:
                self.consumers[callee].append(waiter)
            answers = self.tables[callee]
        for tup in list(answers):
            self._positive_return(waiter, callee, tup)

    def _slice(self, general, pattern, waiter):
        """The answers of a more general table that match a call's
        pattern, without scanning the table: an index on the positions
        the call binds and the general table leaves free, built the
        first time those positions are asked for.  If the table is
        still growing, the index grows with it (_answer), and the call
        waits on its own slice, so a new answer goes only to the calls
        it matches.  (XSB's answer tries index every pattern.)"""
        answers = self.tables[general]
        if None not in pattern and general in self.complete:
            return [pattern] if pattern in answers else ()  # one lookup
        at = tuple(i for i, v in enumerate(pattern)
                   if v is not None and general[1][i] is None)
        want = tuple(pattern[i] for i in at)
        if general not in self.complete:
            self.sliced[general][at, want].append(waiter)
        index = self.indexes.get((general, at))
        if index is None:
            index = self.indexes[(general, at)] = defaultdict(list)
            self.indexed[general].add(at)
            for tup in answers:
                index[tuple(tup[i] for i in at)].append(tup)
        # simplification may since have dropped an answer
        return [t for t in index.get(want, ()) if t in answers]

    def _fold(self, key, aux, callee):
        """Answer an aggregate call from its complete body table."""
        rule = self.sources[aux.pred]
        answers = self.tables[callee]
        if any(UNCONDITIONAL not in c for c in answers.values()):
            raise DatalogError(
                "cannot aggregate over undefined answers (the well-founded "
                "semantics of aggregates is still debated): %s" % rule)
        for tup in fold_answers(rule, aux, answers, key[1]):
            self._answer(key, tup, UNCONDITIONAL)

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
        for at in self.indexed.get(key, ()):    # served calls, by slice
            want = tuple(tup[i] for i in at)
            self.indexes[key, at][want].append(tup)
            for waiter in self.sliced[key].get((at, want), ()):
                self._positive_return(waiter, key, tup)
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
        self._push((caller, head, rest, s, cond))

    def _negative_return(self, waiter, key):
        """Resume a `not` on a completed (and simplified) table."""
        caller, head, rest, subst, cond, _lit = waiter
        value = self._value(("-", key))
        if value is False:
            return
        if value is None:                # undefined: carry it along
            cond = cond | {("-", key)}
        self._push((caller, head, rest, subst, cond))

    # -- the scheduler -------------------------------------------------------

    def query(self, atom):
        """Answers to `atom` under the well-founded semantics, as
        (true, undefined): two sets of tuples.  Every other ground
        instance is false.  Tables are complete when a query returns,
        so they stay, as a table space the next query reads from."""
        check_query_atom(atom, self.arity)
        self.root = root = self._solve(
            (atom.pred, call_pattern(atom, {})), subsume=True)
        true, undefined = set(), set()
        for tup, conds in self.tables[root].items():
            if match(atom.args, tup, {}) is not None:
                (true if UNCONDITIONAL in conds else undefined).add(tup)
        return true, undefined

    def _solve(self, key, subsume=False):
        """Complete the table that answers `key`, and return its
        subgoal; apply() rebuilds a table this way, under its own
        pattern, never served by a more general one."""
        key = self._call(None, key, subsume=subsume)
        try:
            self._evaluate()
        except DatalogError:
            self._reset()           # half-built tables are not complete
            raise
        return key

    def counterexamples(self, undefined=False):
        """The integrity constraints violated in the well-founded model,
        with every body solution, as Engine._counterexamples gives them;
        with undefined=True, the counterexamples that are undefined."""
        return counterexamples(self.goals,
                               lambda goal: self.query(goal)[undefined])

    def _evaluate(self):
        """Local scheduling: run the newest subgoal's frames first.  When
        the top of the completion stack has no work left, see whether it
        is closed — calls nothing older — and settle it there and then,
        before older work runs: complete it, or delay the negations it is
        stuck on.  Repeat until every table is complete."""
        checked = None
        while self.stack:
            while self.ready and not self.work[self.ready[0][1]]:
                heapq.heappop(self.ready)          # drained since queued
            newest = -self.ready[0][0] if self.ready else -1
            # the answer only changes when the stack or the newest work
            # does: the idle tables above it neither run nor call
            if self.order[self.stack[-1]] > newest and \
                    checked != (len(self.stack), newest):
                checked = (len(self.stack), newest)
                group = self._closed_segment()
                if min(self.order[k] for k in group) > newest:
                    self._settle(group)
                    checked = None
                    continue
            self.stats["steps"] += 1
            self._step(self.work[self.ready[0][1]].popleft())

    def _settle(self, group):
        """Complete a closed group with no work left, unless it is stuck
        on negation inside itself.  Delaying all of it would be sound but
        blunt; find its bottom SCC and settle that alone, so a `not` that
        one completion would decide is decided, not delayed."""
        if not any(w[0] in group for k in group for w in
                   chain(self.waiting.get(k, ()), self.folds.get(k, ()))):
            self._complete(group)   # the common case: no Tarjan
            return
        scc = self._bottom_component(group)
        for k in scc:
            if any(w[0] in scc for w in self.folds.get(k, ())):
                raise DatalogError(
                    "aggregation through recursion has no well-founded "
                    "answer here: %s" % self.sources[k[0]])
        stuck = {}
        for k in sorted(scc, key=self.order.get):
            waiting = self.waiting.get(k, ())
            inside = [w for w in waiting if w[0] in scc]
            if inside:
                stuck[k] = inside
                self.waiting[k] = [w for w in waiting if w[0] not in scc]
        if not stuck:
            self._complete(scc)
            return
        # every `not` here waits on its own component: delay
        for k, waiters in stuck.items():
            if self._proved(k):     # true since they suspended
                continue
            for caller, head, rest, subst, cond, _lit in waiters:
                self.stats["delays"] += 1
                self._push((caller, head, rest, subst, cond | {("-", k)}))

    def _closed_segment(self):
        """The smallest top segment of the completion stack that calls
        no incomplete table below it.  The stack is in creation order,
        so "below the segment" is "older than its oldest member": scan
        down from the top, tracking the oldest incomplete table called
        so far, and stop where it is no older than the table reached.
        Only the segment is scanned, and it is about to complete."""
        oldest = float("inf")
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
        if any(conds != {UNCONDITIONAL} for k in scc     # else nothing
               for conds in self.tables[k].values()):  # to settle
            self._simplify(scc)
        for k in sorted(scc, key=self.order.get):
            self.consumers.pop(k, None)
            self.sliced.pop(k, None)      # these tables cannot grow
            self.calls.pop(k, None)          # ...nor be stuck on a call
            for waiter in self.waiting.pop(k, ()):
                self._negative_return(waiter, k)
            for caller, aux in self.folds.pop(k, ()):
                self._fold(caller, aux, k)

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
    add_steps(ap)
    ap.add_argument("-t", "--tables", action="store_true",
                    help="also print every table and the work counters")
    ap.add_argument("-s", "--subsumptive", action="store_true",
                    help="answer a call from a more general table, even one "
                         "still growing, instead of starting one for its "
                         "own pattern")
    args = ap.parse_args(argv)

    engine = SLGEngine(parse(read_program(args.file)), args.subsumptive)
    for atom in run_steps(engine, args.steps):
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
        print("   (%d true, %d undefined; %s, %s, %s%s)"
              % (len(true), len(undefined),
                 _plural(len(engine.tables), "subgoal table"),
                 _plural(engine.stats["completions"], "completion"),
                 _plural(engine.stats["delays"], "delay"),
                 ", %s" % _plural(engine.stats["subsumed calls"],
                                  "subsumed call")
                 if args.subsumptive else ""))
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
    failed = _print_violations([c for c, _g in engine.goals],
                               engine.counterexamples())
    for c, found in engine.counterexamples(undefined=True):
        # neither violated nor satisfied: the model leaves it open
        print("constraint undefined: %s   (%s)"
              % (c, _plural(len(found), "undefined counterexample")))
    return 3 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
