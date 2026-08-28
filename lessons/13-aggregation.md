# Lesson 13 — Aggregation: counting without contradiction

Datalog derives facts; real questions often want *summaries* — how many,
how much, the least, the most. This lesson adds aggregation to the
engine, and the interesting part is not the arithmetic: it is that the
stratification machinery from Lesson 3 turns out to be exactly the
discipline aggregation needs.

## The syntax: one aggregate in the head

```prolog
total(P, sum(A))     :- charge(P, C, A).
howmany(P, count(C)) :- charge(P, C, A).
```

An aggregate term — `sum(V)`, `count(V)`, `min(V)`, `max(V)` — may
appear once in a rule head. The *other* head arguments are the implicit
GROUP BY: `total(P, sum(A))` reads "for each P, the sum of the A values."
Run `programs/spending.dl`:

```
total(alice, 180).      howmany(alice, 2).
total(bob, 990).        howmany(bob, 2).
```

Two semantic decisions worth knowing:

- Aggregation ranges over the **distinct body solutions**, not distinct
  values. Two different charges of 50 sum to 100, because they are two
  rows. This is worth stating precisely, because there is a tempting
  wrong answer: "Datalog is a set language, so 50 and 50 collapse."
  Sets do apply to the body's *solutions*, which are already distinct;
  collapsing the values on top of that is an extra projection, not a
  consequence. The tell that it's wrong: under value-collapsing,
  `count(C)` and `count(A)` give different answers for the same rule
  over the same rows, and an aggregate whose result depends on which
  functionally-determined variable you happen to name cannot be
  defended. SQL, Soufflé, LogicBlox and DDlog all aggregate over
  solutions; so does this engine. (If you *want* distinct values, that
  is SQL's `SUM(DISTINCT A)`: a different, explicitly-requested
  operation.)
- A group with no body solutions produces *no* fact — `count` never
  returns 0, because there is no group to attach it to.

**Drafting habit:** the missing-zero is the aggregation bug people
actually ship. "Alert when a customer has 0 orders" written as
`alert(C) :- orders(C, count(N)), N = 0` can never fire — the customers
you want are exactly the ones producing no group. You need the universe
trick from Lesson 3: a positive predicate to range over, and negation
to find its silent members (`alert(C) :- customer(C), not has_order(C).`).
Whenever an aggregate drives a decision, ask what happens to the rows
that produce no group at all.

## Why an aggregate lives in the head

There is a structural reason aggregation is head-only syntax here (and
in Soufflé, which documents the same restriction): an aggregate answer
has no *witness*. A fact like `path(a, d)` is supported by particular
base facts you can point to; `total(alice, 180)` is supported by no
single charge — it is a property of the whole group, and asking "which
body fact justifies it" has no answer. That is why `--explain` prints
the group rather than a premise chain (exercise 4), and why the
aggregate sits in the head, where a rule states a *conclusion about*
its body solutions rather than joining against one of them.

## Why aggregation is negation in disguise

When is `total(alice, 180)` safe to conclude? Only when every
`charge(alice, ...)` fact that will *ever* be derived already has been —
"finish that relation completely before I summarise it." That is
word-for-word the requirement negation imposed in Lesson 3, and the
implementation is literally the same: an aggregating rule's body edges
are **strict** in the stratification graph, so the aggregate sits in a
higher stratum than what it aggregates, and aggregation inside a
recursive cycle is rejected with the same cycle diagnosis:

```
$ python3 datalog.py cyclic-agg.dl
REJECTED: program is not stratifiable — aggregation occurs inside a
recursive cycle: q --agg--> q.
```

Aggregating a *recursive* relation is perfectly fine; it just lands in
the next stratum (`reach(P, count(Q)) :- connected(P, Q).` in the
example program). What's forbidden is the summary feeding back into what
it summarises. (Letting *monotone* aggregation recurse safely — min
inside shortest-path — is precisely the semiring story of Lesson 7 and
the current research thread behind it; the two lessons are one idea
seen from two sides.)


## Exercises

1. Add `average(P, ...)`. You can't, with one aggregate per head. Build
   it from two rules (`sum` and `count`) and explain why the engine
   can't divide for you (no arithmetic — a deliberate omission the
   README explains).
2. Predict `reach(alice, N)` in `spending.dl` before running it.
   Why does dana not appear at all?
3. Write the forbidden program: make a predicate's count feed its own
   derivation, and read the cycle diagnosis. Then explain in one
   sentence why no answer could be stable.
4. `--explain 'total(bob, 990)'` — what does the tree show instead of
   premises, and why can't an aggregate have a normal premise list?

Next: [tabling](14-tabling.md). The third way to evaluate, and the
secret identity of magic sets.
