# Lesson 12 — Aggregation: counting without contradiction

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
Run `programs/12-spending.dl`:

```
total(alice, 180).      howmany(alice, 2).
total(bob, 990).        howmany(bob, 2).
```

Two semantic decisions worth knowing (both documented choices, both
teachable):

- Aggregation is over the **distinct** (group, value) pairs — Datalog is
  a set language, so two charges of 50 for the same person sum to 50.
  Real systems that want bag semantics carry multiplicities in the data
  (an id column) or in the algebra (Lesson 6's semirings).
- A group with no body solutions produces *no* fact — `count` never
  returns 0, because there is no group to attach it to.

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

Aggregating a *recursive* relation is perfectly fine — it just lands in
the next stratum (`reach(P, count(Q)) :- connected(P, Q).` in the
example program). What's forbidden is the summary feeding back into what
it summarises. (Letting *monotone* aggregation recurse safely — min
inside shortest-path — is precisely the semiring story of Lesson 6 and
the current research thread behind it; the two lessons are one idea
seen from two sides.)

## Is this real, or just academic?

Aggregation is the least optional feature in data systems — GROUP BY is
most of what warehouses do all day — and *recursive* aggregation is a
live commercial frontier: shortest paths, PageRank-style scores, and
bill-of-materials rollups all want aggregates inside recursion, which is
exactly what RelationalAI's semiring machinery and modern SQL
extensions compete on. The stratified form this lesson implements is the
one Soufflé ships today. And the "aggregation = negation" insight is not
a teaching metaphor: production engines' stratifiers treat them
identically, which you can now verify by reading ours.

## Exercises

1. Add `average(P, ...)` — you can't, with one aggregate per head. Build
   it from two rules (`sum` and `count`) and explain why the engine
   can't divide for you (no arithmetic — see the README's "deliberately
   missing" section).
2. Predict `reach(alice, N)` in `12-spending.dl` before running it.
   Why does dana not appear at all?
3. Write the forbidden program: make a predicate's count feed its own
   derivation, and read the cycle diagnosis. Then explain in one
   sentence why no answer could be stable.
4. `--explain 'total(bob, 990)'` — what does the tree show instead of
   premises, and why can't an aggregate have a normal premise list?

Next: [tabling](13-tabling.md) — the third way to evaluate, and the
secret identity of magic sets.
