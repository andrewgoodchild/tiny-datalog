# Lesson 6 — Semirings: what a derivation carries

So far a fact is just true or false. But a derivation *carries* things:
a cost, a count, a set of supporting evidence. Semiring-valued Datalog
(`semiring.py`) generalises evaluation so the same program answers all of
these questions — you only change the algebra.

## The idea

A **semiring** is a set with two operations, "plus" and "times", each
with an identity (0 and 1). Attach a value to every fact. Then:

- a rule instance **multiplies** the values of its body facts
  (a derivation is only as good as everything it used), and
- alternative derivations of the same fact **add**
  (different proofs combine).

Plain Datalog is the boolean semiring: times = and, plus = or.

## One program, four questions

Facts take weights with `@`. `programs/06-routes.dl` is a weighted DAG:

```prolog
edge(a, b) @ 1.   edge(a, c) @ 2.   edge(b, c) @ 1.
edge(b, d) @ 4.   edge(c, d) @ 2.   edge(d, e) @ 3.
path(X, Y) :- edge(X, Y).
path(X, Z) :- edge(X, Y), path(Y, Z).
```

```sh
$ python3 semiring.py --semiring minplus -q 'path(a, d)' programs/06-routes.dl
   path(a, d) = 4          # cheapest route (min over routes, + along a route)

$ python3 semiring.py --semiring count -q 'path(a, d)' programs/06-routes.dl
   path(a, d) = 3          # three distinct routes

$ python3 semiring.py --semiring why -q 'path(a, d)' programs/06-routes.dl
   path(a, d) = {edge(a, b), edge(b, c), edge(c, d)}
              | {edge(a, b), edge(b, d)}
              | {edge(a, c), edge(c, d)}
```

That last one is **why-provenance**: the minimal sets of base facts each
sufficient to derive the conclusion — "which inputs does this answer
depend on," answered by the evaluator itself. Delete all the facts in one
witness set and the answer survives via another; delete one fact from
*every* set and it dies. (Lesson 8 turns exactly that observation into an
algorithm.)

The `bool` semiring reproduces plain Datalog — run it and compare with
`datalog.py`; the test suite does.

## Where the fixpoint went

Evaluation is Kleene iteration: recompute every fact's value from the
previous round's values until nothing changes. For **idempotent**
semirings (bool, minplus, viterbi — where a + a = a) this behaves like
the familiar fixpoint. For counting it converges only when derivations
are finite:

```sh
$ python3 semiring.py --semiring count cyclic.dl   # e.g. add edge(e, a)
                                                   # to 06-routes.dl
error: no fixpoint after 200 rounds — the count semiring diverges on this
program (e.g. counting derivations in a cyclic graph is genuinely infinite)
```

That is not a bug: a cyclic graph really does have infinitely many paths.
Which semirings converge on which programs is the subject of the current
"Datalog over semirings" theory (Green–Karvounarakis–Tannen's provenance
semirings started it in 2007; the convergence story is Abo Khamis, Ngo,
Suciu and colleagues, 2022 onward).

## What's deliberately missing

- **Negation.** What is `not p` when p carries a cost or a witness set?
  There are answers (they need more structure than a semiring), but none
  simple enough for this file. Positive programs only.
- **Semi-naive.** The engine recomputes each round rather than tracking
  deltas — differences of semiring values need subtraction, which
  semirings don't have. Making *that* work is precisely the DBSP insight
  (Lesson 8 discusses it).

## Is this real, or just academic?

Provenance is a compliance product category: data-lineage tooling
("which sources fed this number?") is what GDPR audits and financial
regulators demand, and why-provenance is its formal core — Soufflé ships
a provenance-based debugger for exactly the "why is this fact here?"
question. The min-plus semiring is how routing actually works, from
network protocols to logistics. And the semiring framing itself is the
theory behind RelationalAI's engine and the current push to unify
recursive queries with analytics (counting, summing) — the liveliest
theory-to-industry pipeline in the field right now.

## Exercises

1. Add a second cheap route to `06-routes.dl` and predict all three
   semirings' answers for `path(a, e)` before running them.
2. The `count` semiring ignores weights. Suppose it read `@ n` as a
   multiplicity (n parallel copies of the edge) — what would
   `path(a, d)` become in `06-routes.dl`? (This is bag semantics.)
3. Design a semiring for "the *longest* path" and explain why it
   diverges on cyclic graphs for the same reason counting does.

Next: [probabilistic Datalog](07-probabilistic.md) — the semiring that
almost works, and why its failure matters.
