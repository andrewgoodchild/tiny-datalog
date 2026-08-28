# Lesson 6 — Magic sets: asking questions efficiently

Bottom-up evaluation has a blind spot. Ask `path(n5, X)` — "what can n5
reach?", and the engine computes *every* path in the graph, then throws
away all but the ones starting at n5. Prolog would never do that: it
starts from the query and only explores what's relevant. But Prolog can
loop forever, and we don't want to give up termination or semi-naive.

This blind spot is the standard complaint about bottom-up evaluation —
it *derives many facts that are never used*. The cure has to preserve
what bottom-up is good at, so it cannot simply be "run Prolog".

**Magic sets** is the classical resolution (1986): *rewrite the program*
so that bottom-up evaluation of the rewritten program does what top-down
evaluation of the original would have done. The rewritten program
computes only what the query can observe: the magic predicates are a
running record of *demand* — which bindings some subgoal actually asked
for — and every original rule is guarded to fire only under demand.

## The idea in one example

```sh
$ python3 datalog.py --magic --trace -q 'path(n5, X)' programs/reachability.dl
Magic-sets rewriting (answer predicate path#bf):
  path#bf(X, Y)     :- magic#path#bf(X), edge(X, Y).
  magic#path#bf(Y)  :- magic#path#bf(X), edge(X, Y).
  path#bf(X, Z)     :- magic#path#bf(X), edge(X, Y), path#bf(Y, Z).
  magic#path#bf(n5).
  ...
[magic] 10 IDB facts derived vs 35 under full evaluation
```

Read the pieces:

- **Adornment** `bf`: in the query `path(n5, X)`, the first argument is
  **b**ound, the second **f**ree. `path#bf` is "path, as called with a
  known start point."
- **The magic predicate** `magic#path#bf(X)` means "some subgoal actually
  demands paths starting at X." It's seeded with the query constant
  (`magic#path#bf(n5).`) and grows by the rule that mirrors how the
  recursion passes bindings along: if paths from X are demanded and
  edge(X, Y) exists, then paths from Y are demanded too.
- **Every original rule gets guarded** by the magic predicate, so it can
  only fire for demanded start points.

The result: `magic#path#bf` fills with {n5, n6, n7, n8}, the demanded
subgoals, and evaluation never touches the rest of the graph. 10 facts
instead of 35, same answers, still semi-naive, still guaranteed to
terminate. You've recovered Prolog's goal-direction inside bottom-up
evaluation.

## Different bindings, different rewritings

Ask the reverse question — `path(X, n10)`, "what reaches n10?", and the
rewriting is different: the adornment is `fb`, and following how bindings
flow through `path(X, Z) :- edge(X, Y), path(Y, Z)` produces a *second*
adornment `bb` for the inner call. One predicate, several specializations,
each with its own magic predicate. Try it:

```sh
python3 datalog.py --magic --trace -q 'path(X, n10)' programs/reachability.dl
```

The classic showpiece is the **same-generation** program
(`programs/same-generation.dl`), for "who is in cal's generation?"
magic sets explores only cal's ancestors and their descendants, not the
whole family forest:

```sh
python3 datalog.py --magic --trace -q 'sg(cal, Y)' programs/same-generation.dl
```

## Negation, briefly

This engine takes the simple sound route for `not`: negated subgoals are
never specialized — their predicates (and whatever they depend on) are
included untransformed and computed in full. Specializing *through*
negation is possible but subtle, and it's where the research literature
lives.


## What it costs — measure it, don't assume it

The fact counts above are real, but they are not the whole story, and
the repository ships the generator that shows why. On a 150-node chain
(`python3 benchmarks/generate.py chain 150 > chain150.dl`), the same
rewriting on the same program lands in two very different places:

| query | facts derived | time |
|---|---|---|
| *(full evaluation, no query)* | 11,175 | 0.62s |
| `--magic -q 'path(n140, X)'` | **66** | **0.05s** |
| `--magic -q 'path(n1, X)'` | **11,325** | **2.19s** |

Ask from near the chain's end and demand stays local: 170× fewer facts,
12× faster. Ask from the start and demand propagates the entire chain —
`magic#path#bf` fills with all 150 nodes, so the rewritten program
derives *more* facts than the original (the magic facts themselves) and
every specialised rule now carries a guard literal that each join must
scan. Result: 3.5× slower than not bothering.

The rule to take away is about demand, not about the technique being
good or bad: **magic sets pays in proportion to how much the query's
bindings prune the search.** When demand approaches the whole relation,
the guards are pure overhead. This engine's nested-loop joins amplify
that overhead: an indexed join would make the bad case closer to
break-even, but indexing changes the size of the penalty, not its
existence. Real systems apply magic sets selectively for exactly this
reason.

(Note when reproducing: `--magic --trace` computes a full-evaluation
baseline just to print its comparison line, so time the query *without*
`--trace`.)

## Exercises

1. For the ancestor program of Lesson 1 (`programs/family.dl`),
   compare `-q 'ancestor(abe, X)'` with and without `--magic --trace`.
   How many facts does each derive?
2. Write down, by hand, the rewriting for `ancestor(X, dana)` (adornment
   `fb`). Then check yourself against `--magic --trace`.
3. When does magic *not* help? Two cases, and they fail for different
   reasons — find both. (a) `-q 'path(X, Y)'` with nothing bound:
   explain the counts. (b) On chain-150, `-q 'path(n1, X)'` is bound but
   still loses — time it against plain evaluation and say what the
   binding failed to buy. Then find the crossover: how far along the
   chain must the query start before magic wins on wall-clock?

Next: [semirings](07-semirings.md), which asks what a derivation
carries besides truth.
