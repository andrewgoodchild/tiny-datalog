# Lesson 13 — answers

Runnable rules: `exercises/13-answers.dl`.

**1. `times/3`, and sixteen.**

```prolog
times(n0, Y, n0) :- num(Y).
times(X, Y, Z) :- succ(X1, X), times(X1, Y, Z1), plus(Z1, Y, Z).
```

The recursion is (x+1)·y = x·y + y, with `plus` doing the adding.
`times(n2, n3, Z)` gives n6; `times(n4, n4, Z)` gives **no answers** —
sixteen does not exist in a ten-numeral world, so the product
overflows into absence, exactly as `plus` did. Bounded arithmetic
saturates by omission.

**2. `times(n3, X, n6)`.**

One answer: `times(n3, n2, n6)`. You just performed **division** — six
divided by three — without writing a division rule. The relation
contains all its triples, so any argument can be the unknown; division
is multiplication queried backwards, and (bonus) integer division's
awkward cases surface as answer *counts*: `times(n4, X, n6)` has zero
answers because three-halves is not a numeral, and `times(n0, X, n0)`
has ten, because zero times anything is zero.

**3. `lt/2` over ten numerals.**

```prolog
lt(X, Y) :- succ(X, Y).
lt(X, Z) :- succ(X, Y), lt(Y, Z).
```

The transitive closure of `succ`: one fact per ordered pair, so
10·9/2 = **45**. (It is `path` from Lesson 2 wearing number clothing —
which is the lesson's point made backwards: on a bounded domain,
arithmetic is just graph reachability.)

**4. The mode of `!=`, and why it is harmless.**

Its declaration in this lesson's terms: *both arguments must be ground
at call time* — check-only, never enumerate. The reason `!=` never
threatens termination while `+` does: checking a disequality of two
existing constants creates nothing, but `+` with an unbound result
argument *manufactures a new constant*, and new constants are exactly
what the finiteness argument of Lesson 2 forbids. A built-in is safe
precisely when it can only filter the Herbrand universe, never grow
it.
