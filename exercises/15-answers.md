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

**3. Why do tables reset per query?**

`query()` rebuilds `self.tables` because answers are *per call
pattern*, and a fresh query's patterns may overlap the old ones —
keeping them would be correct (tables are monotone truths) but requires
knowing when a table is *complete* versus still growing. Production
systems keep a shared "table space" with completion tracking for
exactly this reuse, and it is their central engineering artifact.

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
