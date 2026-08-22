# Lesson 8 — Incremental maintenance: don't recompute the world

Databases change. If one edge appears in a million-edge graph, rerunning
the whole fixpoint to update `path` is absurd — the answer differs by a
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

inc = IncrementalEngine(open("programs/02-reachability.dl").read())
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
Initial: 10 path facts

delete("edge(n3, n4).")   — n2's shortcut keeps most paths alive:
  {'deleted': 1, 'over_deleted': 7, 'rederived': 4, 'net_removed': 3}
```

The graph (`programs/08-dred-graph.dl`) is a chain n1..n5 plus a shortcut
edge(n2, n4). Deleting edge(n3, n4) implicates seven facts — the edge
itself plus six paths — but four of the paths, like path(n1, n5),
survive via the shortcut and are re-derived. Only the three
facts genuinely dependent on the dead edge stay dead. The engine then
verifies the repaired state equals a from-scratch recomputation (so do
the tests, for every scenario).

Note the connection to Lesson 6: DRed's phase 1 over-approximates "facts
whose provenance mentions the deleted fact." If you *kept* provenance,
you could delete more surgically — that observation, pushed all the way,
is counting-based maintenance and eventually DBSP.

## Why this is the road to DBSP

DRed's weakness is recomputation in phase 2, and the deeper issue is that
sets can't express "this fact lost one of its two supports." Modern
systems (Differential Dataflow, DBSP — the 2023 boom in incremental
computation) work with **Z-sets**: facts with signed multiplicities,
where an insertion is +1, a deletion is −1, and the algebra of changes
composes through joins, recursion, everything. Semi-naive evaluation and
DRed are both special cases of one uniform derivative rule. That algebra
needs subtraction — exactly the operation Lesson 6's semirings lack —
which is why this module handles change and semiring.py handles values,
and unifying them is a current research frontier.

## What's deliberately missing

Negation. Deleting a fact can *create* derivations through `not`, and
insertions can retract them — maintenance under stratified negation needs
per-stratum bookkeeping this teaching module omits. It rejects such
programs rather than getting them quietly wrong.

## Is this real, or just academic?

This is the hottest commercial corner of the whole course. Incremental
view maintenance is a product category with venture-funded companies in
it: Materialize and Feldera sell exactly "your recursive queries, kept
fresh under change", Snowflake's dynamic tables are the same promise
inside a warehouse, and RDFox maintains billion-fact materialisations
incrementally for enterprise knowledge graphs. DRed, this lesson's
algorithm, is the documented maintenance strategy in several production
reasoners. If one lesson in this course maps directly onto a current
hiring market, it is this one.

## Exercises

1. In the demo graph, which single edge deletion removes the most path
   facts net? Predict, then measure with `delete()`.
2. Construct a case where `over_deleted` is much larger than
   `net_removed` (a well-connected graph). What does that say about
   DRed's worst case?
3. Why does `insert()` never need a re-derive phase? One sentence.

Next: [Horn clauses](09-horn-clauses.md) — the boundary the whole
language lives on.
