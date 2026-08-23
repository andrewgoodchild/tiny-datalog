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

**3. When does magic not help? Two different failures.**

*(a) Nothing bound.* `-q 'ancestor(X, Y)'` — adornment `ff`, the magic
seed is a zero-arity fact that is simply "true", and every guard
passes. Measured: **12 IDB facts vs 14** — the rewriting reproduces
nearly the full computation plus its own bookkeeping. Magic sets
exploits *bindings*; with none there is nothing to exploit. (Same in
SQL: predicate pushdown with no predicate pushes nothing.)

*(b) Bound, but the binding prunes nothing.* On chain-150,
`-q 'path(n1, X)'` is bound — and still loses badly: **11,325 facts and
2.19s, against 11,175 facts and 0.62s** for plain evaluation. The
binding is real but useless, because everything downstream of n1 is
genuinely demanded: the magic set grows to all 150 nodes, so the
rewriting adds 150 magic facts and a guard literal per rule and prunes
nothing. Compare `-q 'path(n140, X)'`: 66 facts, 0.05s — a 12× win. The
governing quantity is how much demand is *smaller* than the relation.

*The crossover.* Measured on chain-150 against 0.63s for plain
evaluation:

| query start | magic time | |
|---|---|---|
| n1 | 2.18s | lose |
| n40 | 1.16s | lose |
| n75 | 0.53s | win (just) |
| n110 | 0.18s | win |
| n140 | 0.05s | win |

The crossover sits near the chain's midpoint, and the advantage
compounds as demand shrinks. That curve — not a single number — is the
honest answer to "is magic sets faster?"
