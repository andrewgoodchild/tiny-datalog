# Lesson 15 — answers

**1. Tables vs magic facts for `ancestor(bob, X)` on
`programs/family.dl`.**

Measured, side by side:

| tabling (`-t`) | magic (`--magic --trace`) |
|---|---|
| table `ancestor(bob, _)` | `magic#ancestor#bf(bob)` |
| table `ancestor(carl, _)` | `magic#ancestor#bf(carl)` |
| table `parent(bob, _)`, `parent(carl, _)` | (EDB literals aren't adorned) |

The `ancestor` call patterns and the magic facts are the same set
{bob, carl}, the compile-time/run-time duality made concrete. The
only difference is bookkeeping style: tabling also tables EDB subgoals,
where magic sets leaves EDB literals untouched.

**2. Why more rounds than answers?**

Iterative QSQR re-solves *every* table from scratch each round, and a
new answer discovered deep in one rule chain only propagates one
"level" per outer round, so rounds track derivation depth, not answer
count. Real SLG engines suspend a consumer exactly where it blocked and
resume it when its table gains an answer, doing each piece of work
once.

Under `slg.py -t` the same query reports `answers returned 8,
clause resolutions 6, ... steps 10`. Each clause is resolved once and
each answer reaches each consumer once. The counter with no
counterpart is the one that is missing: nothing is re-solved, so the
work a round repeats in `tabling.py` simply does not happen.

**3. Which kept tables does a new fact break?**

Add `edge(n8, n9).` to `programs/reachability.dl` after
`path(n5, X)` has run. The kept table `path(n5, X)` is now missing
`path(n5, n9)` and `path(n5, n10)`, and so are the tables between it
and the new fact (`path(n6, X)` to `path(n8, X)`, and `edge(n8, Y)`,
whose pattern matches it). Every table that reads one of those,
directly or not, has to be checked again: `path(n4, X)` gains the
same two answers, and `path(n3, X)`, which already had them through
`n9`, gains none, but no engine knows that without looking. A table
that does not depend on `edge(n8, ...)` can stay. The answer
is a dependency walk: from the changed fact's tables, follow the
calls back to their callers and throw away everything reached. XSB
records those call edges for exactly this (incremental tabling).
Under negation the walk has to go further: a new fact can *remove*
an answer from a table that negates one, which is why Lesson 10's DRed
deletes and then re-derives instead of only adding.

**4. Can tabling create fewer tables than magic creates magic facts?**

For the IDB, no — by construction they are the same demand set: a table
is created exactly when a subgoal pattern is demanded, and a magic fact
is derived exactly when a bound-argument tuple is demanded, through the
same left-to-right binding flow. The honest asymmetry runs the other
way: tabling also creates tables for EDB subgoals (see exercise 1), so
its table *count* can exceed the magic-fact count, never undercut the
demand it represents.

**5. Eight queens at other sizes, and with the literals swapped.**

N = 2 and N = 3 have no solutions: every square in the second column
is attacked by any queen in the first, and on a 3×3 board the third
column is always attacked. The counts for N = 4, 5, 6 are 2, 10 and 4,
and `TablingTests` checks them under tabling, magic sets and plain
bottom-up.

Swap the literals so that `queensK(...) :- nextK(...), queensK-1(...)`
and the answers are unchanged, but the tables explode:

| Board | tables, as shipped | tables, swapped |
|---|---|---|
| 6×6 | 442 | 12,139 |
| 7×7 | 1,090 (0.1s) | 189,134 (30s) |

Top-down evaluation passes bindings left to right. As shipped,
`queensK-1` runs first and binds the earlier queens, so `nextK` is only
ever asked about boards that are already valid. Swapped, `nextK` is
called with nothing bound and must enumerate its whole relation, the
same relation that sinks plain bottom-up evaluation. Literal order is
the *sideways information passing* of Lesson 7. It never changes the
answer, but in a goal-directed engine it decides how much work there
is.

**6. An undefined answer with two conditions.**

`exercises/15-answers.dl` gives position a two moves, to b and to c,
and each of those can only move back:

```
$ python3 slg.py exercises/15-answers.dl -q 'win(a)'
?- win(a)   [SLG]
   win(a).   undefined: if not win(b); or if not win(c)
```

Each condition is one rule instance that could have made `win(a)`
true: moving to b wins if b is a losing position, and moving to c wins
if c is. Either would do, which is why the conditions are joined by
"or". Neither can be settled, because b and c are losing exactly when a
is winning, so both stay open and `win(a)` is undefined. The
well-founded model agrees: `datalog.py --models` puts `win(a)`,
`win(b)` and `win(c)` all in its undefined zone.
