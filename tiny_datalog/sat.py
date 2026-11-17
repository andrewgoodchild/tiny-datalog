#!/usr/bin/env python3
"""
sat.py — a small SAT solver: DPLL, in forty lines.  (Lesson 26 reads
it; lesson 5 uses it too.)

A **clause** is a list of non-zero integers: 3 means "variable 3 is
true", -3 "variable 3 is false", and the clause holds when any one of
them does.  `solve` finds an assignment under which every clause holds,
or reports that there is none.

Two modules pose their search as clauses and hand it here:

* synthesis.py: one variable per candidate rule, on or off, with
  clauses learned from provenance (lesson 26);
* semantics.py: one variable per ground atom, true or false, with
  clauses from the program's rules and from each failed candidate
  model (lesson 5).

Both use the solver the same way.  It proposes; something that knows
what the variables mean checks the proposal, and answers with a clause
when it is wrong.  The solver itself knows nothing about Datalog.

What is left out is what makes industrial solvers fast: learning a
clause from every conflict, watching two literals per clause where
this copies the clause list, and restarts.  Tens of variables and
hundreds of clauses are comfortable; thousands are not.
"""

from __future__ import annotations


def solve(clauses):
    """A satisfying assignment, as the set of variables that are true,
    or None if there is none.  DPLL: propagate unit clauses, then
    branch.  The branch tries *false* first, on the highest-numbered
    variable, so answers lean towards few true variables and, among
    those, towards low numbers: callers number what they would
    rather have first."""

    def assign(clauses, lit):
        out = []
        for c in clauses:
            if lit in c:
                continue                    # satisfied
            if -lit in c:
                c = [x for x in c if x != -lit]
                if not c:
                    return None             # conflict
            out.append(c)
        return out

    if not all(clauses):
        return None                         # an empty clause: no way out
    stack = [([list(c) for c in clauses], frozenset())]
    while stack:
        todo, model = stack.pop()
        while todo:
            unit = next((c[0] for c in todo if len(c) == 1), None)
            if unit is None:
                break
            todo, model = assign(todo, unit), model | {unit}
            if todo is None:
                break
        if todo is None:
            continue                        # backtrack
        if not todo:
            return {lit for lit in model if lit > 0}
        var = max(abs(lit) for c in todo for lit in c)
        for lit in (var, -var):             # popped last-in first: off, then on
            reduced = assign(todo, lit)
            if reduced is not None:
                stack.append((reduced, model | {lit}))
    return None
