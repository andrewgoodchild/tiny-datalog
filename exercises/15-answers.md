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

**3. Predict what `-u 'edge(n3, n9)~.'` rebuilds.**

```
$ python3 slg.py programs/reachability.dl -q 'path(n1, X)' -u 'edge(n3, n9)~.' -q 'path(n1, X)'
...
% update edge(n3, n9)~.   (4 tables rebuilt, 0 unchanged, 16 untouched)
```

The retracted edge matches one table, `edge(n3, Y)`. Walking the calls
back up gives `path(n3, X)`, `path(n2, X)` and `path(n1, X)`, so four
tables are reached. Nothing stops the walk early, because each of the
three loses `n9` and `n10`, and so each changes what its caller reads.
The other 16 tables, among them `path(n9, X)`, which nothing calls
now, are untouched. Compare lesson 15's `edge(n8, n9).`, where
`path(n3, X)` came out the same and the two tables above it were kept.

For the second part, add `r(c)` and `q(c)` in one update:

```
r(a). r(b). q(b).
p(X) :- r(X), not q(X).
t(X) :- p(X).
```

Query `t(X)` (answer: `a`), then apply `r(c). q(c).`. The new `r(c)`
reaches `r(X)`, so `p(X)` is rebuilt. But `q(c)` cancels it out, and
`p(X)` comes out as `{a}` again. `t(X)` reads only `p(X)`, so it is put
back without a rebuild: `apply` returns `(2, 1)`. The `q(c)` table did
not exist before the update; the rebuilt `p(X)` calls it for the first
time and builds it fresh. That is why every reached table is set aside
before any is rebuilt.

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
