# Lesson 6 — Semirings: what a derivation carries

> **Heavier going than lessons 1–5.** This one uses a little algebra —
> semirings, quotients, a small impossibility proof. If that is not
> your background, read to the end of "One program, four questions",
> then skip to the summary box before the exercises. The result you
> need for lessons 7 and 8 is just: *the same program computes
> different things if you change what a derivation carries.*

So far a fact is just true or false. But a derivation *carries* things:
a cost, a count, a set of supporting evidence. Semiring-valued Datalog
(`semiring.py`) generalises evaluation so the same program answers all of
these questions. You only change the algebra.

## The idea

A **semiring** is a set with two operations, "plus" and "times", each
with an identity (0 and 1). Attach a value to every fact. Then:

- a rule instance **multiplies** the values of its body facts
  (a derivation is only as good as everything it used), and
- alternative derivations of the same fact **add**
  (different proofs combine).

Plain Datalog is the boolean semiring: times = and, plus = or.

## One program, four questions

Facts take weights with `@`. `programs/routes.dl` is a weighted directed acyclic graph:

```prolog
edge(a, b) @ 1.   edge(a, c) @ 2.   edge(b, c) @ 1.
edge(b, d) @ 4.   edge(c, d) @ 2.   edge(d, e) @ 3.
path(X, Y) :- edge(X, Y).
path(X, Z) :- edge(X, Y), path(Y, Z).
```

```sh
$ python3 semiring.py --semiring minplus -q 'path(a, d)' programs/routes.dl
   path(a, d) = 4          # cheapest route (min over routes, + along a route)

$ python3 semiring.py --semiring count -q 'path(a, d)' programs/routes.dl
   path(a, d) = 3          # three distinct routes

$ python3 semiring.py --semiring why -q 'path(a, d)' programs/routes.dl
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

## Can you compute provenance once and specialise later?

A real design-review question. Why-provenance is the expensive
semiring — witness sets are big, and someone will propose computing it
once and deriving the cheap answers from it afterwards by applying a
function. When is that sound?

The condition is exact: a map `h : K → K'` commutes with evaluation
precisely when it is a **semiring homomorphism** — `h(a + b) = h(a) +
h(b)`, `h(a × b) = h(a) × h(b)`, and it preserves 0 and 1. Then
specialising after the fact gives the same answer as evaluating in `K'`
from the start, on every program.

`exercises/06-homomorphism.py` checks two candidates and gets two
different answers.

**why → minplus works.** A witness set costs the sum of its facts; a
set of alternatives costs the cheapest. That sends why's `plus` (set
union) to `min` and its `times` (pairwise union) to `+`:

```
$ python3 exercises/06-homomorphism.py
why -> minplus, over 06-routes.dl:
  path(a, b)     h(why)=1     minplus=1     ok
  ...
  => agrees on every fact
```

**why → count does not exist.** Run `programs/two-derivations.dl`,
where a second rule reaches the same conclusion from the same facts by
a different route:

```
  q(a, c) why   = {e(a, b), e(b, c)}      p(a, c) why   = {e(a, b), e(b, c)}
  q(a, c) count = 2                       p(a, c) count = 1
```

Two facts with **identical** why-values and different counts. That is a
proof, not a hunch: any function of the why-value must give them the
same answer, and the correct answers differ. No homomorphism can exist.

The reason is structural, and it has a name: this is **universal
algebra**, the study of algebraic structures through their operations
and equations. **Provenance polynomials** — ℕ[X], where each derivation
contributes a monomial and multiplicities are kept — are the **free**
commutative semiring on the base facts. Free is a precise promise:
assign each base fact a value in *any* commutative semiring K, and that
assignment extends to exactly one homomorphism ℕ[X] → K. That
universal property is the whole "factors through" claim in one line —
evaluate in polynomials once, and every semiring's answer is one
homomorphism away, *because nothing else satisfies the equations more
freely*.

Why-provenance is a **quotient** of the free object: impose the extra
equations of absorption (A + A·B = A) and idempotence, and the
polynomial collapses to witness sets — keeping which facts were needed,
discarding how many ways they combined. Quotients only ever merge;
once information is identified away, no function recovers it. That is
the entire impossibility proof above, restated as algebra: `count`
needs a distinction the quotient erased.

So the design-review answer: **materialise the polynomial and you may
specialise to anything; materialise why-provenance and you may only
specialise to semirings that don't need multiplicity**: the idempotent
and absorptive ones, like minplus, max-min, and boolean. Counting,
probability-by-summation, and anything else that distinguishes two
routes through the same facts must be computed from the polynomial or
from scratch.

## Where this is going

This lesson's fixpoint is deliberately naive because semi-naive needs
subtraction and semirings have none. The current research thread —
**Datalog°** (Abo Khamis, Ngo, Pichler, Suciu, Wang) — takes exactly
that problem seriously: define program semantics as a least fixpoint in
an *ordered* semiring, then characterise which algebraic properties
make the fixpoint converge and which ones let semi-naive evaluation
still be sound. It is Lesson 3's stratification and this lesson's
algebra treated as one question, and it is the frontier this module
sits just underneath. (The thread is personal as well as technical:
Val Tannen, of the 2007 provenance-semirings paper this lesson rests
on, is also an author of DBSP, Lesson 8's algebra of changes — the
same mathematician, working the two sides of the missing subtraction.)

## What's deliberately missing

- **Negation.** What is `not p` when p carries a cost or a witness set?
  There are answers (they need more structure than a semiring), but none
  simple enough for this file. Positive programs only.
- **Semi-naive.** The engine recomputes each round rather than tracking
  deltas — differences of semiring values need subtraction, which
  semirings don't have. Making *that* work is precisely the DBSP insight
  (Lesson 8 discusses it).


## Exercises

1. Add a second cheap route to `routes.dl` and predict all three
   semirings' answers for `path(a, e)` before running them.
2. The `count` semiring ignores weights. Suppose it read `@ n` as a
   multiplicity (n parallel copies of the edge) — what would
   `path(a, d)` become in `routes.dl`? (This is bag semantics.)
3. Design a semiring for "the *longest* path" and explain why it
   diverges on cyclic graphs for the same reason counting does.
4. Write `h : why → minplus` yourself before reading
   `exercises/06-homomorphism.py`, and check it against
   `--semiring minplus` on `routes.dl`. Which of the two semiring
   axioms is the one you have to think about?
5. Construct your own program where `why → count` fails — two
   derivations of one fact from one set of base facts. Then explain
   why the same trick cannot break `why → bool`.

Next: [probabilistic Datalog](07-probabilistic.md). The semiring that
almost works, and why its failure matters.
