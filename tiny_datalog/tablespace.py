"""
tablespace.py — the table space both tabled engines keep (lesson 15):
tables that survive from one query to the next, and through a change
to the facts.  That is incremental tabling, eager or lazy.

A table is a subgoal's answers, and a subgoal is a predicate with a
call pattern: the values of its bound arguments, None for the free
ones (call_pattern).  Each engine records which tables read which as
it solves (`callers`), and TableSpace walks those edges back up when
a fact changes: only what the walk reaches can see the change.  The
-q and -u steps of both tabled CLIs are here too.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from tiny_datalog.core import (
    _tarjan, Const, DatalogError, match, parse, parse_goal, validate)
from tiny_datalog.lattice import free_value, improve


def call_pattern(atom, subst):
    """The call pattern of an atom under a substitution: the bound
    arguments' values, None where still free."""
    out = []
    for a in atom.args:
        if isinstance(a, Const):
            out.append(a.value)
        elif a.name in subst:
            out.append(subst[a.name])
        else:
            out.append(None)
    return tuple(out)


def head_seed(head, pattern):
    """Unify a clause head with a call pattern: one-way matching, as
    in a join, over the bound positions only (a free position, None,
    constrains nothing).  The substitution, or None if they clash."""
    bound = [(a, v) for a, v in zip(head.args, pattern) if v is not None]
    return match([a for a, _v in bound], [v for _a, v in bound], {})


class TableSpace:
    """Incremental tabling, shared by both tabled engines: the table
    space survives a change to the facts.  Every call is recorded as an
    edge from caller to callee (`callers`), the dependency graph the
    queries walked.  apply() changes the facts, then finds the tables
    the change can reach: each one whose pattern matches a changed
    fact, and every table that read one of those, directly or not.  The
    rest cannot see the change and stay as they are.

    The reached tables are rebuilt from empty, callee before caller,
    one strongly connected group at a time.  A group none of whose
    callees came out different is put back as it was, unrebuilt, so
    the walk stops at the first table an update leaves unchanged.
    Rebuilding from empty is what makes it right under negation: a new
    fact can *remove* an answer from a table that negates it, which
    adding answers alone would miss (Lesson 10's DRed meets the same
    problem bottom-up, and deletes before it re-derives).

    With lazy=True the reached tables are only marked stale: each is
    rebuilt when a query next reaches it, and one no query reaches
    costs nothing (XSB's lazy incremental tabling).  A stale table
    keeps its old answers in `old`, for the early stop, and the stale
    tables it read in `reads`; `hit` holds the stale tables that must
    be rebuilt whatever their inputs do.  A stale table is never read:
    it is out of `tables`, so a call to it builds it afresh."""

    def apply(self, script, lazy=False):
        """Insert facts and retract `fact~.` ones; returns (tables
        rebuilt, tables the change reached but left as they were),
        both 0 when lazy.  The script is checked whole before anything
        changes."""
        clauses = parse(script)
        for c in clauses:
            if c.body or c.weight is not None:
                raise DatalogError("apply() takes facts, and `fact~.` to "
                                   "retract one, only: %s" % c)
        self.arity = validate(clauses, self.arity)
        changed = defaultdict(list)       # (pred, arity) -> changed facts
        for c in clauses:
            facts = self.by_pred[(c.head.pred, len(c.head.args))]
            fact = (c.head, ())
            if (fact in facts) == c.retract:            # a real change
                if c.retract:       # every copy: `p(a). p(a).` is legal
                    facts[:] = [f for f in facts if f != fact]
                else:
                    facts.append(fact)
                changed[(c.head.pred, len(c.head.args))].append(c.head)
        dead = [k for k in list(self.tables) + list(self.old)
                for head in changed.get((k[0], len(k[1])), ())
                if head_seed(head, k[1]) is not None]
        self.hit.update(dead)
        reached = set()
        while dead:                       # walk the calls back up
            k = dead.pop()
            if k not in reached:
                reached.add(k)
                for caller in self.callers.get(k, ()):
                    # an edge outlives a caller a rebuild did not
                    # remake (a later -s call may be served instead)
                    if caller in self.tables or caller in self.old:
                        self.reads[caller].add(k)
                        dead.append(caller)
        live = reached.intersection(self.tables)
        self.old.update((k, self.tables[k]) for k in live)
        self._forget(live)
        return (0, 0) if lazy else self._revalidate(set(self.old))

    def _revalidate(self, keys):
        """Bring stale tables up to date, with every stale table they
        read: rebuild them callee first, and put back each group whose
        inputs came out unchanged.  Returns (rebuilt, put back), and
        adds them to `repairs`.  queries call this on their subgoal."""
        todo, stack = set(), [k for k in keys if k in self.old]
        while stack:
            k = stack.pop()
            if k not in todo:
                todo.add(k)
                stack += self.reads.get(k, ())
        old = {k: self.old.pop(k) for k in todo}   # no longer stale
        reads = {k: self.reads.pop(k, set()) for k in todo}
        hit, self.hit = self.hit & todo, self.hit - todo
        keys = sorted(todo, key=str)      # patterns mix None and values
        num = {k: i for i, k in enumerate(keys)}
        scc = _tarjan(range(len(keys)), [(num[u], num[v], False)
                                         for u in keys for v in reads[u]])
        groups = defaultdict(list)
        for k in keys:
            groups[scc[num[k]]].append(k)
        changed, rebuilt = set(), 0
        for i in sorted(groups):          # Tarjan numbers callees first
            group = groups[i]
            if not hit.intersection(group) and not any(
                    v in changed for k in group for v in reads[k]):
                for k in group:           # nothing it reads changed
                    if k not in self.tables:
                        self._restore(k, old[k])
                continue
            for k in group:
                if k not in self.tables:
                    self._solve(k)
                rebuilt += 1
                if self.tables.get(k) != old[k]:
                    changed.add(k)
        for k in todo:                    # stale readers left behind
            self._settled(k, k in changed)
        self.repairs.update(rebuilt=rebuilt, unchanged=len(todo) - rebuilt)
        return rebuilt, len(todo) - rebuilt

    def _settled(self, key, changed=True):
        """A stale table is live again.  A stale table that read it
        must be rebuilt if it changed, or if a call built it afresh
        (`changed` left True), since then nothing compares it with what
        it was.  Both engines call this as they make a table."""
        if self.old.pop(key, None) is not None:
            self.repairs["rebuilt"] += 1  # built afresh, by this call
        self.hit.discard(key)
        self.reads.pop(key, None)
        for k, callees in self.reads.items():
            if key in callees:
                callees.discard(key)
                if changed:
                    self.hit.add(k)

    def _reset_space(self):
        self.callers = defaultdict(set)   # table -> tables that read it
        self.old = {}                     # stale table -> its answers
        self.reads = defaultdict(set)     # stale table -> stale callees
        self.hit = set()                  # stale tables to rebuild
        self.repairs = Counter()          # _revalidate's work, in total

    def _forget(self, keys):
        for k in keys:
            self.tables.pop(k, None)
            self.complete.discard(k)
            self.best.pop(k, None)

    def _key(self, atom, subst):
        """The subgoal a call reads (lattice.free_value says why)."""
        return (atom.pred, free_value(self.lattice, atom.pred,
                                      call_pattern(atom, subst)))

    def _improve(self, key, tup):
        """lattice.improve, on this table space's tables."""
        return improve(self.lattice, self.best, key, self.tables[key], tup)

    def _restore(self, key, answers):
        self.tables[key] = answers
        self.complete.add(key)


def add_steps(ap):
    """-q and -u for both tabled CLIs, kept in the order given: queries,
    and changes to the facts between them, as `steps`."""
    ap.add_argument("-q", "--query", dest="steps", action="append",
                    default=[], type=lambda q: ("q", q), metavar="ATOM",
                    help="goal to solve (repeatable)")
    ap.add_argument("-u", "--update", dest="steps", action="append",
                    type=lambda u: ("u", u), metavar="FACTS",
                    help="change the facts before the queries after it: "
                         "`e(a, b).` inserts, `e(a, b)~.` retracts")
    ap.add_argument("--lazy", action="store_true",
                    help="-u only marks the tables it reaches stale; a "
                         "query rebuilds the ones it reads")


def run_steps(engine, steps, lazy=False):
    """Apply and report each -u in turn, yielding each -q's goal for
    the CLI to solve in between; when lazy, report after each query
    what it rebuilt."""
    for kind, text in steps:
        if kind == "q":
            done = Counter(engine.repairs)
            yield parse_goal(text)
            done = engine.repairs - done
            if lazy and done:
                print("%% rebuilt on demand: %d table%s, %d unchanged; "
                      "%d still stale"
                      % (done["rebuilt"], _s(done["rebuilt"]),
                         done["unchanged"], len(engine.old)))
            continue
        if lazy:
            engine.apply(text, lazy=True)
            print("%% update %s   (%d table%s stale, %d live)"
                  % (text.strip(), len(engine.old), _s(len(engine.old)),
                     len(engine.tables)))
            continue
        before = len(engine.tables)   # a rebuild may add or drop some
        rebuilt, same = engine.apply(text)
        print("%% update %s   (%d table%s rebuilt, %d unchanged, "
              "%d untouched)"
              % (text.strip(), rebuilt, _s(rebuilt), same,
                 before - rebuilt - same))


def _s(n):
    return "" if n == 1 else "s"
