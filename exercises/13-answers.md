# Lesson 13 — answers

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
