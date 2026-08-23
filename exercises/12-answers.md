# Lesson 12 — answers

Runnable rules for exercise 1: `exercises/12-answers.dl`.

**1. `average` from `sum` and `count`.**

```prolog
spend_sum(P, sum(A))     :- charge(P, C, A).
spend_count(P, count(C)) :- charge(P, C, A).
average_parts(P, S, N)   :- spend_sum(P, S), spend_count(P, N).
```

`average_parts(alice, 180, 2)` — the division is the consumer's job,
because dividing requires arithmetic over *derived* values, which is a
built-in, which is deliberately missing (README, "Deliberately
missing"): a built-in must fire at the moment its operands bind, and
this engine refuses to make join order semantically significant.

**2. `reach(alice, N)` — and dana's absence.**

`reach(alice, 3)`: alice is connected to bob, carol, and dana. dana
produces *no* `reach` fact at all — she knows no one, so the body has
no solutions for her, so there is no group. `count` never returns 0
because a zero-count group has nothing to attach the zero to; if you
want "dana: 0" you need a universe predicate and negation, which is a
nice extra exercise.

**3. The forbidden program.**

```prolog
p(a, 1).
q(count(X)) :- q(Y), p(X, N).
```

```
REJECTED: program is not stratifiable — aggregation occurs inside a
recursive cycle: q --agg--> q.
```

Why no answer could be stable, in one sentence: the count is only
correct once `q` is complete, but the count itself adds to `q` —
"complete" can never arrive, the same knot as `p :- not p` with
counting in place of negation.

**4. `--explain` on an aggregate.**

```
total(bob, 990)   [via total(P, sum(A)) :- charge(P, C, A).]
  = sum over 2 distinct values of A: {90, 900}
```

Instead of premises, the tree shows the *group*: an aggregate fact
isn't supported by any single body fact — remove either charge and the
conclusion doesn't weaken, it *changes*. That non-monotonicity is
exactly why aggregation lives a stratum up, and why its explanation is
a set, not a chain.
