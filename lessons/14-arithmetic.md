# Lesson 14 — Arithmetic: the price of numbers

Every newcomer asks this in week one. Here is the engine's answer:

```
$ python3 datalog.py sum.dl        # p(Z) :- q(X), Z = X + 1.
error: line 2: unexpected character '='
```

Not "unsupported feature" — the *tokenizer* doesn't know the
character. Arithmetic is the course's most deliberate omission, and
this lesson is the reasoning: numbers break both pillars the language
stands on, every workaround lives inside a fence you already know, and
every production engine's arithmetic is some way of paying for numbers
without giving up the termination theorem.

## Why a built-in breaks the machine

Suppose `Z = X + 1` were allowed. What kind of thing is it?

As a *relation*, it is infinite — `{(0,1), (1,2), (2,3), …}` — and
Lesson 3's safety discipline exists precisely to keep infinite
relations out: there is no way to *enumerate* it, only to *check* it
once its arguments are bound. But "once its arguments are bound"
smuggles in something Datalog has never had: the rule body now works
only in some orders. `q(X), Z = X + 1` succeeds where
`Z = X + 1, q(X)` flounders, and join order — until now a pure
performance choice the engine was free to make (Lesson 2) — becomes
part of what a program *means*. Engines that take this path must add a
**mode discipline**: every built-in declares which arguments it needs
ground, and safety checking grows from one rule into a dataflow
analysis.

The deeper problem is Lesson 11's fence wearing a disguise. The
integers under successor *are* a free term algebra — `n+1` is `s(n)`
spelled differently — so admitting unbounded arithmetic is admitting
function symbols, and the Herbrand universe goes infinite exactly as
it did there. SQL demonstrates the price: `WITH RECURSIVE` allows
arithmetic in recursion, and in exchange a recursive SQL query has no
termination guarantee at all — Lesson 2's theorem, traded away in one
feature.

## What you can do inside the fence

**Bound the numbers and they become ordinary data.**
`programs/bounded-arithmetic.dl` builds ten numerals and one relation:

```prolog
succ(n0, n1). succ(n1, n2). ... succ(n8, n9).

num(X) :- succ(X, _).
num(X) :- succ(_, X).

plus(n0, Y, Y) :- num(Y).
plus(X, Y, Z) :- succ(X1, X), plus(X1, Y, Z1), succ(Z1, Z).
```

```
$ python3 datalog.py -q 'plus(n2, n3, Z)' programs/bounded-arithmetic.dl
?- plus(n2, n3, Z)
   plus(n2, n3, n5).
   (1 answer)
```

Three things fall out that a built-in would not give you. Overflow is
*absence* — `plus(n7, n5, Z)` has zero answers, which under Lesson 4's
closed-world reading is the honest overflow flag. The relation is
*reversible* — `plus(X, Y, n4)` returns all five splits of four,
because bottom-up evaluation computes the whole relation and a query
is just a filter (Lesson 11's Peano program gets the same reversibility
top-down, one solution at a time). And `--explain plus(n2, n3, n5)`
prints a counting proof, since arithmetic done as derivation has
derivations.

**Aggregation is the sanctioned arithmetic.** Lesson 13's `sum`,
`count`, `min` and `max` do real number-crunching — but only in the
head, over a finished group, a stratum above the recursion they
summarise. That placement is not a syntax quirk; it is exactly the
discipline that keeps the arithmetic from feeding back into the
enumeration.

**Weights push numbers into the algebra.** Lesson 8's `@` annotations
do costs and probabilities without a single number ever appearing *in
a rule* — the semiring multiplies along derivations while the logic
stays pure. That is the cleanest of the three answers: numbers as
values facts carry, not terms rules build.

## How the real engines pay

- **Soufflé** ships arithmetic functors with a groundness requirement —
  the mode discipline above, made official.
- **Answer set programming** grounds integer variables over declared
  finite ranges — bounded arithmetic as an industrial strategy — and
  when ranges get large the grounding explodes, which is why the
  real-world train scheduling in Lesson 0's deployments list runs
  clingo *hybridised with a difference-logic solver* rather than
  grounding times into atoms.
- **Constrained Horn clauses** (Lesson 11's closing note) go the other
  way entirely: keep the clause shape, hand every arithmetic literal
  to an SMT solver, accept undecidability, and get the language modern
  program verification actually uses.

One design axis, one trade: how much arithmetic, against how much of
the termination theorem survives.

## Exercises

1. Add `times/3` to the bounded program (you will need `plus`), and
   predict `times(n4, n4, Z)` before running it. What is the bounded
   answer to "sixteen"?
2. `times(n3, X, n6)` — run it, and say what operation you just
   performed without writing a rule for it.
3. Define `lt(X, Y)` and predict how many facts it holds over ten
   numerals before counting.
4. Lesson 1's exercise 4 added `X != Y` as a built-in with both
   arguments required bound. State its mode declaration in this
   lesson's terms, and explain why `!=` never threatens termination
   while `+` does.

Next: [tabling](15-tabling.md) — the third way to evaluate, and the
secret identity of magic sets.
