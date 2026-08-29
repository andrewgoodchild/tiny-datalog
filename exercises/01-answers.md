# Lesson 1 — answers

Runnable rules: `exercises/01-answers.dl`.

**1. `cousin(X, Y)`, and yes, it misbehaves, twice.**

```prolog
cousin(X, Y) :- parent(PX, X), parent(PY, Y), sibling(PX, PY).
```

Because `sibling` contains every self-pair (`sibling(bob, bob)` — the
lesson's bug), everyone whose parent "is their own sibling" becomes
their own cousin, and actual siblings count as cousins too (their
parents are the same person, who is their own sibling). Nothing here is
wrong *logically*. The rules say exactly this, and being forced to
notice it is the lesson.

**2. `aunt_or_uncle(A, N)`: a sibling of a parent.**

```prolog
aunt_or_uncle(A, N) :- parent(P, N), sibling(P, A).
```

Three literals as required. Same defect inherited: with no `X != Y`
built-in, every parent is a sibling of themselves and therefore their
own children's "aunt or uncle". The fix needs a disequality built-in —
see the README's list of deliberate omissions for why the engine
doesn't have one, and exercise 4 below for how you'd add it.

**3. Predict `-q 'parent(X, carl)'`.**

Exactly one answer: `parent(bob, carl).` The constant filters, the
variable binds; it is a lookup, not a computation.

**4. Adding `X != Y`.**

The sketch (deliberately not merged — it's your exercise): a `neq`
token or reserved predicate in the parser; a safety rule that both
arguments must be bound by earlier positive literals (an unbound
disequality would mean "for some value they differ" — always true — or
force enumeration of an open domain); and evaluation as a filter in
`_rule_substitutions`, exactly where negated literals filter. Note the
order sensitivity you must handle: the check can only run once both
variables are bound, which is why real engines treat built-ins as a
scheduling problem. The README's list of deliberate omissions is
this exercise's design discussion.

