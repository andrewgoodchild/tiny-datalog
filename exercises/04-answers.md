# Lesson 4 — answers

**1. `ancestor(abe, X)` with and without `--magic` on
`programs/01-family.dl`.**

Measured: magic derives **11 IDB facts vs 14** under full evaluation.
The margin is modest because abe is the root — nearly everything is
relevant to him. Ask from the leaf instead (`ancestor(bob, X)`) and the
pruning is dramatic: 1 `ancestor#bf` fact and 2 magic facts, against
the same 14. Demand-driven evaluation pays off in proportion to how
*specific* the demand is.

**2. The rewriting for `ancestor(X, dana)` (adornment `fb`), by hand.**

The head binds only the second argument, so bindings flow differently:

```prolog
% base rule: nothing binds X before parent is scanned
ancestor#fb(X, Y) :- magic#ancestor#fb(Y), parent(X, Y).
% recursive rule: parent(X, Y) binds both, so the inner call is bb
magic#ancestor#bb(Y, Z) :- magic#ancestor#fb(Z), parent(X, Y).
ancestor#fb(X, Z) :- magic#ancestor#fb(Z), parent(X, Y), ancestor#bb(Y, Z).
% ...plus the bb specialisation's own copies of both rules
magic#ancestor#fb(dana).
```

One query, two adornments (`fb` and `bb`) — check every line against
`--magic --trace -q 'ancestor(X, dana)'`.

**3. When does magic not help?**

`-q 'ancestor(X, Y)'` — nothing bound, adornment `ff`, the magic seed is
a zero-arity fact that is simply "true", and every guard passes.
Measured: **12 IDB facts derived vs 14** — the rewriting reproduces
nearly the full computation plus its own bookkeeping. Magic sets is a
way to exploit *bindings*; with no bindings there is nothing to
exploit. (The same holds in SQL: predicate pushdown with no predicate
pushes nothing.)
