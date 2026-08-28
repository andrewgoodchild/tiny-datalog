# Lesson 9 — Incremental maintenance: don't recompute the world

Databases change. If one edge appears in a million-edge graph, rerunning
the whole fixpoint to update `path` is absurd: the answer differs by a
handful of facts. Incremental view maintenance repairs the materialised
relations instead. `incremental.py` implements both directions for
positive programs.

## Insertions are semi-naive, resumed

Lesson 2's discipline — *new facts this round must use something new from
last round* — is not just an optimisation; it's a maintenance algorithm.
The database is a fixpoint of the old facts, so any genuinely new
derivation must pass through an inserted fact. Seed the delta with the
insertions and run the same loop:

```python
from incremental import IncrementalEngine

inc = IncrementalEngine(open("programs/reachability.dl").read())
inc.insert("edge(n8, n1).")
# {'inserted': 1, 'derived': ...}   — only the new consequences
```

## Deletions need two phases: DRed

Deletion is harder for a reason worth sitting with: a derived fact that
*used* a deleted fact might still be derivable another way. Support is
not a chain, it's a web. DRed (delete-and-rederive, 1993) resolves this
with deliberate overkill:

1. **Over-delete.** Remove every fact that has *any* derivation through a
   deleted fact — computed with the same delta-joins as semi-naive, but
   marking casualties instead of deriving news.
2. **Re-derive.** Some casualties were innocent: they still have
   derivations from the surviving facts. Run derivation seeded from the
   survivors and put them back.

Run the built-in demo:

```sh
$ python3 incremental.py
Initial: 10 path facts, materialised in 0.000s

delete("edge(n3, n4).")   — n2's shortcut keeps most paths alive:
  {'deleted': 1, 'over_deleted': 7, 'rederived': 4, 'net_removed': 3}
```

The graph (`programs/dred-graph.dl`) is a chain n1..n5 plus a shortcut
edge(n2, n4). Deleting edge(n3, n4) implicates seven facts: the edge
itself plus six paths, but four of the paths, like path(n1, n5),
survive via the shortcut and are re-derived. Only the three
facts genuinely dependent on the dead edge stay dead. The engine then
verifies the repaired state equals a from-scratch recomputation (so do
the tests, for every scenario).

Note the connection to Lesson 7: DRed's phase 1 over-approximates "facts
whose provenance mentions the deleted fact." If you *kept* provenance,
you could delete more surgically — that observation, pushed all the way,
is counting-based maintenance and eventually DBSP.

## The case that makes it obvious

`programs/supply-chain.dl` (Lesson 2) is where this stops being an
optimisation. The materialisation is 8,766 facts over a dependency
graph, and the world changes in exactly one way: a CVE is published.

```python
>>> inc = IncrementalEngine(open("programs/supply-chain.dl").read())
>>> inc.insert("vulnerable(pkg40, cve_2026_0002).")
{'inserted': 1, 'derived': 12}
```

Twelve new facts, 0.03 seconds, against 0.81 to rebuild, and the new
CVE turns out to reach *every* service, which nobody predicted by
looking. This is the shape of the real workload: the rules never
change, the graph rarely changes, and the vulnerability feed changes
daily. Recomputing a closure from scratch because one fact arrived is
the thing incremental maintenance exists to stop.

## Deleting without the demolition: Backward/Forward

DRed's over-delete phase is honest about its own name. Watch it handle
the deletion of `depends(pkg4, pkg13)` — the exact edge the README's
`--explain` tree told you to bump:

```sh
$ python3 incremental.py programs/supply-chain.dl -u 'depends(pkg4, pkg13)~.'
materialised: 8766 facts
depends(pkg4, pkg13)~.
  -> {'deleted': 1, 'over_deleted': 112, 'rederived': 111, 'net_removed': 1} in 0.846s
```

It tore down 112 facts and rebuilt 111 of them to remove **one** — the
deleted edge itself. Every derived fact survived, because pkg4 also
reaches pkg13 through pkg8. (Notice what that means for the security
story: bumping the dependency from the derivation tree changed nothing.
`uses(pkg4, pkg13)` is still true and pkg4 is still exposed. The
`--explain` tree shows you *a* route; Lesson 7's why-provenance is the
tool that shows you *every* witness set you would have to break.)

The 2015 successor — **Backward/Forward** (Motik, Nenov, Piro and
Horrocks; the algorithm inside RDFox) — refuses to demolish first. It
computes the same affected set, then checks each fact by *backward
chaining* for an alternative derivation before touching it:

```sh
$ python3 incremental.py programs/supply-chain.dl -u 'depends(pkg4, pkg13)~.' --strategy bf
materialised: 8766 facts
depends(pkg4, pkg13)~.
  -> {'deleted': 1, 'affected': 112, 'confirmed': 111, 'removed': 1, 'backward_checks': 112} in 1.529s
```

Same end state (the tests check both against a fresh recomputation, on
this program and on hundreds of fuzzed ones), but the 111 survivors were
never disturbed: no teardown, no rebuild, one removal. That matters in
a real system where every touched fact means locks taken, indexes
updated, and downstream consumers notified.

Two honest observations, one per direction:

- **Wall-clock goes the other way here.** On this engine B/F is
  *slower* (about 1.5s to DRed's 0.85s on the run above) even though it
  touches almost nothing, because each backward step is a scan — this
  engine has no indexes, so goal-directed probing pays the same tax
  magic sets paid in Lesson 6. The number B/F optimises is facts
  disturbed, and it wins on wall-clock only once lookups are cheap.
- **The backward search must be well-founded.** A path fact around a
  cycle can "derive" another doomed path fact forever; support only
  counts if it bottoms out in facts that don't need the deleted one.
  The implementation carries the current proof path and refuses to let
  a fact support itself through it — and this is the same phenomenon as
  Lesson 7's diverging count semiring. Counting-based maintenance
  (track how many derivations support each fact, decrement on delete)
  is the third classical strategy, and cyclic derivations are exactly
  why it is restricted to non-recursive rules: on a cycle, the count
  never honestly reaches zero.

## Why this is the road to DBSP

DRed pays teardown-and-rebuild; B/F pays proof search; and the deeper
issue under both is that sets can't express "this fact lost one of its
two supports." **DBSP** (Budiu, Chajed, McSherry, Ryzhyk, Tannen —
VLDB 2023) dissolves the problem instead of solving it: represent
relations as **Z-sets**, collections where every fact carries a signed
integer multiplicity. An insertion is +1, a deletion is −1, and a
*change is just data*, flowing through the same operators as everything
else. Every operator — join, union, recursion — has a uniform
derivative: given a change to the input, compute the change to the
output algebraically. Semi-naive evaluation and DRed both fall out as
special cases of one rule, and the entire strategy debate this lesson
just measured evaporates, because there is no deletion algorithm to
choose. Recursion is handled by making the fixpoint iteration itself a
dimension changes can flow through (a stream of streams) — the part of
the theory that genuinely goes beyond resumed semi-naive.

This is shipping, not prospectus. The DBSP authors built **Feldera**, a
Rust engine you program in SQL — including recursive views — whose
contract is that the incrementally maintained answer is *identical* to
recomputing from scratch on the current data. That is the same
invariant this module's tests assert after every update, held at
industrial scale. Its close relative **Materialize** is built on
differential dataflow, the earlier operational form of the same
insight; DBSP is best read as its algebraic formalisation, making
"incrementalise this program" a mechanical transformation rather than
per-operator engineering.

One name ties this lesson to Lesson 7: Val Tannen is both the Tannen of
Green–Karvounarakis–**Tannen** (the 2007 provenance-semirings paper)
and a DBSP author. The connection is not biographical trivia — the
algebra of changes needs subtraction, exactly the operation Lesson 7's
semirings lack, which is why this module handles *change* and
semiring.py handles *values*, and why unifying them is a current
research frontier.

## What's deliberately missing

Negation. Deleting a fact can *create* derivations through `not`, and
insertions can retract them — maintenance under stratified negation needs
per-stratum bookkeeping this teaching module omits. It rejects such
programs rather than getting them quietly wrong.


## Exercises

1. In the demo graph, which single edge deletion removes the most path
   facts net? Predict, then measure with `delete()`.
2. Construct a case where `over_deleted` is much larger than
   `net_removed` (a well-connected graph). What does that say about
   DRed's worst case?
3. Why does `insert()` never need a re-derive phase? One sentence.
4. Run exercise 2's diamond deletion under `--strategy bf` and predict
   `backward_checks` before you look. Then construct the opposite case:
   a graph where B/F must do *many* failed checks because everything
   affected genuinely dies. Which strategy would you pick for each, and
   what single property of the graph decides it?

Next: [Horn clauses](10-horn-clauses.md). The boundary the whole
language lives on.
