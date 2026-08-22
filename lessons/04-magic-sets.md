# Lesson 4 — Magic sets: asking questions efficiently

Bottom-up evaluation has a blind spot. Ask `path(n5, X)` — "what can n5
reach?" — and the engine computes *every* path in the graph, then throws
away all but the ones starting at n5. Prolog would never do that: it
starts from the query and only explores what's relevant. But Prolog can
loop forever, and we don't want to give up termination or semi-naive.

**Magic sets** is the classical resolution (1986): *rewrite the program*
so that bottom-up evaluation of the rewritten program does what top-down
evaluation of the original would have done.

## The idea in one example

```sh
$ python3 datalog.py --magic --trace -q 'path(n5, X)' programs/02-reachability.dl
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

The result: `magic#path#bf` fills with {n5, n6, n7, n8} — the demanded
subgoals — and evaluation never touches the rest of the graph. 10 facts
instead of 35, same answers, still semi-naive, still guaranteed to
terminate. You've recovered Prolog's goal-direction inside bottom-up
evaluation.

## Different bindings, different rewritings

Ask the reverse question — `path(X, n10)`, "what reaches n10?" — and the
rewriting is different: the adornment is `fb`, and following how bindings
flow through `path(X, Z) :- edge(X, Y), path(Y, Z)` produces a *second*
adornment `bb` for the inner call. One predicate, several specializations,
each with its own magic predicate. Try it:

```sh
python3 datalog.py --magic --trace -q 'path(X, n10)' programs/02-reachability.dl
```

The classic showpiece is the **same-generation** program
(`programs/04-same-generation.dl`) — for "who is in cal's generation?"
magic sets explores only cal's ancestors and their descendants, not the
whole family forest:

```sh
python3 datalog.py --magic --trace -q 'sg(cal, Y)' programs/04-same-generation.dl
```

## Negation, briefly

This engine takes the simple sound route for `not`: negated subgoals are
never specialized — their predicates (and whatever they depend on) are
included untransformed and computed in full. Specializing *through*
negation is possible but subtle, and it's where the research literature
lives.

## Is this real, or just academic?

The specific transformation ships: Soufflé offers a magic-set transform,
and the LogicBlox engine (now RelationalAI's lineage) built its
"demand transformation" on this idea. But the broader principle is one
of the most commercial ideas in data systems: *push what you know about
the query into the evaluation*. Every SQL optimizer's predicate pushdown,
every "filter early, join late" rewrite, every distributed engine
shipping filters to the data — all are the magic-sets instinct wearing
different clothes. Learn it here in its purest form and you will
recognise it in every query plan you ever read.

## Exercises

1. For the ancestor program of Lesson 1 (`programs/01-family.dl`),
   compare `-q 'ancestor(abe, X)'` with and without `--magic --trace`.
   How many facts does each derive?
2. Write down, by hand, the rewriting for `ancestor(X, dee)` (adornment
   `fb`). Then check yourself against `--magic --trace`.
3. When does magic *not* help? Try `-q 'path(X, Y)'` (nothing bound) and
   explain the counts you see.

Next: [beyond stratification](05-beyond-stratification.md) — what a
program means when no stratification exists, and the café paradox.
