# Lesson 3 — answers

Runnable rules: `exercises/03-answers.dl`.

**1. `has_no_children(X)`.**

```prolog
person(X) :- parent(X, Y).
person(Y) :- parent(X, Y).
is_parent(X) :- parent(X, Y).
has_no_children(X) :- person(X), not is_parent(X).
```

Answers: carl and dana. Two things the exercise wanted you to trip on:
negation needs a *universe* (`person`, derived from the data — safety
forbids `not is_parent(X)` with unbound X), and you cannot negate
`parent(X, Y)` directly for this purpose because Y would be unbound
under the `not` — hence the `is_parent` helper that projects Y away
first.

**2. Nodes on no cycle.**

```prolog
on_cycle(X)  :- path(X, X).
off_cycle(X) :- node(X), not on_cycle(X).
```

On the graph a→b→c→a, c→d: `off_cycle(d)` only. `--trace` reports
**two strata**: `path` and `on_cycle` together in stratum 1 (positive
dependencies only), `off_cycle` in stratum 2, above the negation.

**3. win/move on an acyclic chain — still rejected.**

It is, and must be: stratification is a property of the *rules*, not
the data. `win` depends on `not win` syntactically, whatever the move
graph contains; the engine cannot know the data keeps the recursion
harmless without evaluating, and that gamble is exactly what the
stratified semantics refuses to take. The semantics that *does* consult the
ground program is lesson 5's (`--models` accepts this program and finds
its unique stable model).
