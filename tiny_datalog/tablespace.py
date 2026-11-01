"""
tablespace.py — the table space both tabled engines keep (lesson 15):
tables that survive from one query to the next, and through a change
to the facts.  That is incremental tabling, eager or lazy.  The tables
also explain themselves: each answer records how it was first derived,
and explain() prints the tree those records make.

A table is a subgoal's answers, and a subgoal is a predicate with a
call pattern: the values of its bound arguments, None for the free
ones (call_pattern).  Each engine records which tables read which as
it solves (`callers`), and TableSpace walks those edges back up when
a fact changes: only what the walk reaches can see the change.  The
-q, -e and -u steps of both tabled CLIs are here too.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import count

from tiny_datalog.core import (
    _tarjan, Atom, Const, DatalogError, _format_value, aggregate_of,
    format_atom, is_comparison, match, parse, parse_goal, sort_key,
    validate)
from tiny_datalog.lattice import free_value, improve

UNCONDITIONAL = frozenset()   # the empty condition: the answer is true


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
                    v in changed for k in group for v in reads[k]) \
                    and not self._cites_lost(group):
                for k in group:           # nothing it reads changed
                    if k not in self.tables:
                        self._restore(k, old[k])
                self._restamp(group)
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
        self.why = {}         # table -> answer -> condition -> derivation
        self.ticks = count(1)             # ...each stamped, in order
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
        self.tables[key] = answers        # why[key] was kept for it
        self.complete.add(key)

    # -- explanations --------------------------------------------------------

    def _cites_lost(self, group):
        """Whether a group's derivations cite a lattice answer no table
        records any more.  A rebuild that came out the same may reach
        its best by other steps, so the answers compare equal while the
        values bettered on the way differ; then the group is rebuilt,
        or explain() would have nothing to show for what they cite."""
        if not self.lattice:
            return False
        have = {(k[0], t) for k, why in self.why.items() if k[0] in
                self.lattice and (k in self.tables or k in group)
                for t in why}
        return any(not lit.negated and lit.atom.pred in self.lattice and
                   (lit.atom.pred, tuple(
                       a.value if isinstance(a, Const) else s[a.name]
                       for a in lit.atom.args)) not in have
                   for k in group for why in self.why.get(k, {}).values()
                   for _t, (_h, body), s in why.values() for lit in body)

    def _restamp(self, keys):
        """Stamp a put-back group's derivations again, in their order,
        after the rebuilt tables below that they read: then each
        premise still has a derivation older than what cites it."""
        records = sorted(((r, why, cond) for k in keys
                          for why in self.why.get(k, {}).values()
                          for cond, r in why.items()), key=lambda x: x[0][0])
        for r, why, cond in records:
            why[cond] = (next(self.ticks),) + r[1:]

    def _record(self, key, tup, cond, clause, subst):
        """Note how an answer first came to hold under a condition (the
        empty one, true, in tabling.py): the clause, as indexed, and
        the substitution that solved its body, stamped in order.  Each
        premise was already an answer then, so it was stamped before."""
        self.why[key].setdefault(tup, {}).setdefault(
            cond, (next(self.ticks), clause, subst))

    def explain(self, atom):
        """Why each answer to `atom` holds: a derivation tree per answer,
        read off the records the engine kept as it derived them, where
        datalog.py's --explain searches a materialisation for one.  An
        undefined answer (slg.py) shows a derivation under one of its
        conditions.  Returns the lines."""
        self.query(atom)
        proofs = self._proofs()
        lines = []
        for found in sorted((a for a, (status, _r) in proofs.items()
                             if a[0] == atom.pred and status != "bettered"
                             and match(atom.args, a[1], {}) is not None),
                            key=lambda a: sort_key(a[1])):
            lines += self._tree(found, proofs)
        return lines

    def _proofs(self):
        """{(pred, answer): (status, derivations)} over the live tables:
        "true" with its true derivations, "undefined" with those of its
        conditions, or "bettered" for a lattice answer a better one has
        replaced.  That one held of a value derived, and derivations
        stamped before the better one may rest on it.  Each list is in
        stamp order, one entry per table that holds the answer."""
        found = {}
        for key, why in self.why.items():
            answers = self.tables.get(key)
            if answers is None:
                continue                  # stale, or forgotten
            for tup, records in why.items():
                if tup in answers:
                    conds = (answers[tup] if isinstance(answers, dict)
                             else {UNCONDITIONAL})
                    rank, status, mine = (
                        (0, "true", [records[UNCONDITIONAL]])
                        if UNCONDITIONAL in conds else
                        (2, "undefined", [records[c] for c in conds]))
                elif UNCONDITIONAL in records:
                    rank, status, mine = 1, "bettered", [
                        records[UNCONDITIONAL]]
                else:
                    continue
                atom = (key[0], tup)
                old = found.get(atom)
                if old is None or rank < old[0]:
                    found[atom] = (rank, status, mine)
                elif rank == old[0]:
                    old[2].extend(mine)
        return {a: (status, sorted(mine, key=lambda r: r[0]))
                for a, (_r, status, mine) in found.items()}

    @staticmethod
    def _premise(derivations, before):
        """The derivation a premise is read with, for one stamped
        `before` that cites it: the oldest, which is older than that
        (each premise was an answer when cited; a rebuilt table's are
        stamped anew, and so is anything put back above it)."""
        return derivations[0]

    def _tree(self, top, proofs):
        """One answer's derivation tree, as datalog.explain draws one:
        depth first, with an explicit stack, each premise indented under
        what it proves."""
        lines, shown = [], set()
        stack = [(0, top, float("inf"))]
        while stack:
            indent, item, before = stack.pop()
            pad = "  " * indent
            if isinstance(item, str):
                lines.append(pad + item)
                continue
            label = format_atom(*item)
            if item not in proofs:
                lines.append(pad + label + "   (not in any table)")
                continue
            status, derivations = proofs[item]
            tick, clause, subst = self._premise(derivations, before)
            if not clause[1]:
                lines.append(pad + label + "   (base fact)")
                continue
            if item in shown:
                lines.append(pad + label + "   (derivation shown above)")
                continue
            shown.add(item)
            note = {"true": "", "undefined": "   undefined"}.get(status)
            if note is None:              # a lattice's: name what beat it
                i = self.lattice[item[0]][0]
                note = "   (since bettered: %s)" % ", ".join(
                    format_atom(*a) for a, (st, _r) in proofs.items()
                    if a[0] == item[0] and st == "true" and
                    a[1][:i] + a[1][i + 1:] == item[1][:i] + item[1][i + 1:])
            aux = clause[1][0].atom
            if aux.pred in self.sources:  # an aggregate, folded
                rule = self.sources[aux.pred]
                lines.append("%s%s   [via %s]%s" % (pad, label, rule, note))
                lines.append(pad + "  = " + self._group(rule, aux, item[1],
                                                         proofs))
                continue
            rule = self.shown[clause]
            lines.append("%s%s   [via %s]%s" % (pad, label, rule, note))
            children = []
            for lit in rule.body:
                tup = tuple(a.value if isinstance(a, Const) else subst[a.name]
                            for a in lit.atom.args)
                if is_comparison(lit):
                    children.append("  %s   (comparison)" % Atom(
                        lit.atom.pred, tuple(Const(v) for v in tup)))
                elif lit.negated:
                    undefined = proofs.get((lit.atom.pred, tup),
                                           ("",))[0] == "undefined"
                    children.append("  not %s   (%s)" % (
                        format_atom(lit.atom.pred, tup),
                        "undefined" if undefined else "no such answer"))
                else:
                    children.append((lit.atom.pred, tup))
            stack.extend((indent + (not isinstance(c, str)), c, tick)
                         for c in reversed(children))
        return lines

    def _group(self, rule, aux, tup, proofs):
        """The values an aggregate folded, read off its body's table."""
        idx, func, var = aggregate_of(rule.head)
        k, at = len(rule.head.args) - 1, aux.args.index(var)
        group = tup[:idx] + tup[idx + 1:]
        values = sorted((t[at] for (p, t), (status, _r) in proofs.items()
                         if p == aux.pred and status == "true"
                         and t[:k] == group), key=lambda v: sort_key((v,)))
        return "%s over %d body solution%s of %s: [%s]" % (
            func, len(values), _s(len(values)), var,
            ", ".join(map(_format_value, values)))


def add_steps(ap):
    """-q, -e and -u for both tabled CLIs, kept in the order given:
    queries, explanations, and changes to the facts between them, as
    `steps`."""
    ap.add_argument("-q", "--query", dest="steps", action="append",
                    default=[], type=lambda q: ("q", q), metavar="ATOM",
                    help="goal to solve (repeatable)")
    ap.add_argument("-e", "--explain", dest="steps", action="append",
                    type=lambda e: ("e", e), metavar="ATOM",
                    help="solve a goal and print a derivation tree for "
                         "each answer, read off the tables (repeatable)")
    ap.add_argument("-u", "--update", dest="steps", action="append",
                    type=lambda u: ("u", u), metavar="FACTS",
                    help="change the facts before the queries after it: "
                         "`e(a, b).` inserts, `e(a, b)~.` retracts")
    ap.add_argument("--lazy", action="store_true",
                    help="-u only marks the tables it reaches stale; a "
                         "query rebuilds the ones it reads")


def run_steps(engine, steps, lazy=False):
    """Apply and report each -u, and print each -e's trees, in turn,
    yielding each -q's goal for the CLI to solve in between; when lazy,
    report after each query what it rebuilt."""
    for kind, text in steps:
        if kind in "qe":
            done = Counter(engine.repairs)
            if kind == "q":
                yield parse_goal(text)
            else:
                goal = parse_goal(text)
                print("?- explain %s" % goal)
                for line in engine.explain(goal) or ["(no answers)"]:
                    print("   " + line)
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
