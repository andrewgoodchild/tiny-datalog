# Lesson 3 — Negation and stratification

Plain Datalog is *monotone*: adding facts can only add conclusions. Lots
of questions aren't like that. *Which nodes are unreachable? Which birds
can't fly? Who has no manager?* For those you need `not`.

## Negation as failure

```prolog
node(a). node(b). node(c). node(d).
edge(a, b). edge(b, c).
reach(a).
reach(Y) :- reach(X), edge(X, Y).
unreached(X) :- node(X), not reach(X).
```

`not reach(X)` succeeds when `reach(X)` is *not derivable* — negation as
failure, a closed-world reading: what I cannot prove, I take to be false.
Here `unreached` = {d}.

Two ground rules come with it:

**Safety.** Every variable under `not` must be bound by a positive
literal in the same rule. `unreached(X) :- not reach(X).` is rejected —
"everything that isn't reachable" over an open universe of constants is
not a well-defined relation. The `node(X)` literal supplies the universe.

**Order of computation.** To evaluate `not reach(X)` you must be *done*
computing `reach`. If you check `not reach(d)` while `reach` is still
growing, you might say yes today and be wrong tomorrow.

## Stratification

That ordering requirement generalizes: slice the program into **strata**
so that each predicate's negated dependencies live in strictly lower
strata, then compute the strata in order, each to fixpoint. Run
`--trace` on `programs/05-cafe-foodary.dl` and you'll see the engine do
exactly this:

```
Stratification:
  stratum 1: eats_at_home/1, household_cooks/1
  stratum 2: conclusion1_violated/1, ..., eats_in_cafe/1
```

The classic non-monotone idiom this enables is **default reasoning**
(Tweety, `programs/03-tweety.dl`):

```prolog
bird(tweety). bird(opus). penguin(opus).
abnormal(X) :- penguin(X).
flies(X) :- bird(X), not abnormal(X).
```

Birds fly *unless proven abnormal*. Add a fact (`penguin(tweety)`) and a
conclusion (`flies(tweety)`) disappears — non-monotonicity, tamed by
stratification.

## When stratification fails

What if negation sits *inside* a recursive loop?
(`programs/03-win.dl`)

```prolog
move(a, b).  move(b, a).
win(X) :- move(X, Y), not win(Y).
```

"A position is winning if it has a move to a losing position." `win`
depends negatively on itself — no stratum ordering exists, and the engine
refuses:

```
REJECTED: program is not stratifiable — negation occurs inside a
recursive cycle: win --not--> win.
```

Note carefully what this does and doesn't mean. It's a *syntactic*
verdict: this engine's evaluation strategy can't order the computation.
It does **not** by itself mean the program is meaningless — this very
program has two perfectly sensible "solutions" ({win(a)} and {win(b)}).
Making that precise needs better semantics, which is Lesson 5.

Meanwhile the truly pathological case looks the same syntactically
(`programs/03-barber.dl`):

```prolog
person(barber). person(plato).
shaves(barber, X) :- person(X), not shaves(X, X).
```

The barber shaves exactly those who don't shave themselves. Does the
barber shave the barber? Russell's paradox as a Datalog program — also
rejected, and here the rejection is hiding something genuinely broken.
Lesson 5 separates the two cases.


## Exercises

1. Write `has_no_children(X)` over the family data from Lesson 1.
2. Compute nodes on *no* cycle: first `on_cycle(X)`, then negate it.
   How many strata does `--trace` report?
3. Take the win/move game and give it a move graph with no cycles (a
   chain of 4 positions). It stratifies? No — check with the engine, and
   work out why the *rules*, not the *data*, are what stratification
   looks at.

Next: [magic sets](04-magic-sets.md) — how to stop computing the whole
world when you asked one question.
