# Lesson 8 — answers

Runnable graph for exercise 2: `exercises/08-answers.dl`.

**1. Which single edge deletion removes the most path facts net?**

Measured over `programs/dred-graph.dl`, `net_removed` per edge:

| deleted edge | over_deleted | rederived | net_removed |
|---|---|---|---|
| edge(n1, n2) | 4 | 0 | **5** |
| edge(n4, n5) | 4 | 0 | **5** |
| edge(n2, n3) | 7 | 5 | 3 |
| edge(n3, n4) | 7 | 5 | 3 |
| edge(n2, n4) | 5 | 5 | 1 |

The chain's *end* edges hurt most, because nothing routes around them,
while the shortcut edge(n2, n4) barely matters (everything it carried
survives via n3). Damage is a function of redundancy, not position in
the file.

**2. over_deleted ≫ net_removed.**

The diamond in `exercises/08-answers.dl`: deleting `edge(s, m1)`
implicates six facts (the edge, `path(s, m1)`, and the four paths
s→t→u...) — over-delete sweeps them all, but the four through-paths
survive via m2 and are re-derived; only the edge and `path(s, m1)`
are truly gone (`over_deleted: 6, rederived: 4, net_removed: 2`).
DRed's worst case is exactly a
well-connected graph: the more redundant the derivations, the more
phase 1 over-reacts and phase 2 repairs. That is precisely the case
`--strategy bf` exists for — see exercise 4 — and counting-based
maintenance (track *how many* derivations support each fact) is the
third answer, restricted to non-recursive rules for the reason the
lesson gives.

**3. Why does `insert()` never need a re-derive phase?**

One sentence: insertion is monotone — new facts can only *add*
derivations, never invalidate one, so nothing previously derived is
ever in doubt.

**4. B/F on the diamond, and its opposite case.**

On the diamond, `delete("edge(s, m1).", strategy="bf")` reports
`affected: 6, confirmed: 4, removed: 2, backward_checks: 6` — one
check per affected fact, each of the four through-paths confirmed on
its first alternative derivation (via m2). B/F's best case.

The opposite case is a bare chain: delete the first edge of
`a->b->c->d->e` and every path fact out of `a` genuinely dies. B/F must
run a *failed* backward search for each — and a failed search is the
expensive kind, because it exhausts every rule and every candidate
match before giving up — while DRed deletes the lot and its re-derive
phase finds nothing to do almost immediately.

The property that decides it is **derivation redundancy**: how many
independent ways the affected facts can be derived. Redundant graph →
B/F (survival is confirmed cheaply, and survivors are never touched);
brittle graph → DRed (there is nothing to save, so demolition is the
efficient move). Neither dominates, which is why both are in the
module and real systems ship hybrids.
