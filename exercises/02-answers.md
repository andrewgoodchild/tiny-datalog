# Lesson 2 — answers

Runnable rules: `exercises/02-answers.dl`.

**1. `same_component` over directed edges.**

Symmetrise first, then close:

```prolog
link(X, Y) :- edge(X, Y).
link(X, Y) :- edge(Y, X).
same_component(X, Y) :- link(X, Y).
same_component(X, Z) :- same_component(X, Y), link(Y, Z).
```

With edges a→b, c→b, d→e: {a, b, c} are mutually connected and {d, e}
separately — `same_component(a, c)` holds even though no directed path
joins them.

**2. Bill of materials, chain of 6 parts.**

`has_part` derives 15 facts (all ordered pairs down the chain) in **5
rounds of new facts** — one per containment depth: `--trace` shows
+5, +4, +3, +2, +1, then fixpoint. Depth of recursion = number of
rounds; that is semi-naive's shape on any chain.

**3. Fewest rounds on a 16-node chain.**

Measured (`benchmarks/generate.py chain 16`, counting `--trace` round
lines including the fixpoint round):

| variant | rounds |
|---|---|
| right-linear `edge, path` | 16 |
| left-linear `path, edge` | 16 |
| non-linear `path, path` | **6** |

The non-linear rule doubles reachable path length every round —
logarithmic rounds — while both linear forms extend length by one. Run
`--naive --trace` on the same input and watch the "tuples derived"
column grow while the deltas shrink: that widening gap is the entire
argument for semi-naive.
