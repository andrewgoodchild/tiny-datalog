# Lesson 8 — answers

Runnable graph for exercise 2: `exercises/08-answers.dl`.

**1. Which single edge deletion removes the most path facts net?**

Measured over `programs/08-dred-graph.dl`, `net_removed` per edge:

| deleted edge | over_deleted | rederived | net_removed |
|---|---|---|---|
| edge(n1, n2) | 5 | 0 | **5** |
| edge(n4, n5) | 5 | 0 | **5** |
| edge(n2, n3) | 7 | 4 | 3 |
| edge(n3, n4) | 7 | 4 | 3 |
| edge(n2, n4) | 5 | 4 | 1 |

The chain's *end* edges hurt most — nothing routes around them — while
the shortcut edge(n2, n4) barely matters (everything it carried
survives via n3). Damage is a function of redundancy, not position in
the file.

**2. over_deleted ≫ net_removed.**

The diamond in `exercises/08-answers.dl`: deleting `edge(s, m1)`
implicates six facts (the edge, `path(s, m1)`, and the four paths
s→t→u...) — over-delete sweeps them all — but the four through-paths
survive via m2 and are re-derived; only the edge and `path(s, m1)`
are truly gone (`over_deleted: 6, rederived: 4, net_removed: 2`).
DRed's worst case is exactly a
well-connected graph: the more redundant the derivations, the more
phase 1 over-reacts and phase 2 repairs. (Counting-based maintenance —
track *how many* derivations support each fact — is the standard answer,
and the road to DBSP.)

**3. Why does `insert()` never need a re-derive phase?**

One sentence: insertion is monotone — new facts can only *add*
derivations, never invalidate one, so nothing previously derived is
ever in doubt.
