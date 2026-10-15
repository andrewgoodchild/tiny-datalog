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

Three literals as required. Same defect inherited: without `X != Y`,
every parent is a sibling of themselves and therefore their own
children's "aunt or uncle". The fix is a disequality, `P != A` at the
end of the body; exercise 4 below is how it works, and why it is safe
when `+` is not (lesson 14).

**3. Predict `-q 'parent(X, carl)'`.**

Exactly one answer: `parent(bob, carl).` The constant filters, the
variable binds; it is a lookup, not a computation.

**4. Adding `X != Y`.**

The design: a comparison token in the parser; a safety rule that both
arguments must be bound by positive literals (an unbound disequality
would mean "for some value they differ" — always true — or force
enumeration of an open domain); and evaluation as a filter, exactly
where negated literals filter. Note the order sensitivity you must
handle: the check can only run once both variables are bound, which is
why real engines treat built-ins as a scheduling problem.

The engine's version, for comparison, lives in `core.py`. The parser
stores `X != Y` as an atom whose predicate is the operator, so every
module that walks a body sees it; `validate` applies the safety rule;
`body_order` schedules positives first, then comparisons, then
negations; and `holds` evaluates one. The scheduling problem shows up
once more in `magic.py`, which must hold a comparison back until the
rewriting has bound its variables. Lesson 14's exercise 4 is why
comparisons made it in and `+` did not.

