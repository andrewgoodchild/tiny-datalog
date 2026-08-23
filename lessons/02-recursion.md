# Lesson 2 — Recursion and semi-naive evaluation

The queries SQL historically couldn't ask are the recursive ones: *who are
all my ancestors? what can this function reach? which parts contain this
part, at any depth?* Recursion is where Datalog stops being a notation for
joins and becomes a language.

## Transitive closure

The canonical recursive program (`programs/02-reachability.dl`):

```prolog
path(X, Y) :- edge(X, Y).                 % base case
path(X, Z) :- edge(X, Y), path(Y, Z).     % recursive case
```

`path` is defined in terms of itself. Bottom-up evaluation handles this
naturally: paths of length 1 appear first, then length 2 (built from an
edge plus a length-1 path), and so on, until a round adds nothing new.

Termination is guaranteed: no rule can invent new constants, so there are
finitely many possible facts, and the fact set only grows. Every Datalog
program terminates — this is the deep trade against Prolog and general
logic programming, bought by banning function symbols.

## Watching it run

```sh
$ python3 datalog.py --trace programs/02-reachability.dl
Semi-naive evaluation:
  stratum 1 (path):
    round 1: +9 path
    round 2: +8 path
    round 3: +7 path
    ...
    round 8: no new facts — fixpoint
```

**Naive** evaluation would re-run every rule against the *whole* database
each round — rediscovering every already-known path every time.
**Semi-naive** evaluation, what this engine does, only joins each rule
against the *delta*: the facts that were new in the previous round. A new
path this round must use a path discovered last round; anything else was
already found. The shrinking `+9, +8, +7...` counts in the trace are the
deltas.

You can measure what that saves rather than take it on trust. Generate
a 100-node chain and run it both ways:

```sh
python3 benchmarks/generate.py chain 100 > chain100.dl
python3 datalog.py chain100.dl            # semi-naive: 0.23s
python3 datalog.py --naive chain100.dl    # naive:     10.6s
```

**46× on a hundred nodes**, and the gap widens with depth: naive
evaluation redoes every derivation in every round, so its total work
grows with rounds × relation size while semi-naive's grows with the
relation. Add `--trace` to either run to watch the mechanism —
semi-naive prints shrinking deltas, naive prints a "tuples derived"
count that climbs while the deltas shrink. That climbing number is
wasted work, quantified.

This one idea — track what changed, derive only its consequences — is the
ancestor of modern incremental view maintenance (Differential Dataflow,
DBSP).

## Shapes of recursion

**Right- vs left- vs non-linear.** These all compute transitive closure:

```prolog
path(X, Z) :- edge(X, Y), path(Y, Z).     % right-linear
path(X, Z) :- path(X, Y), edge(Y, Z).     % left-linear
path(X, Z) :- path(X, Y), path(Y, Z).     % non-linear: doubles path length per round
```

Try the non-linear one with `--trace`: it reaches fixpoint in ~log(n)
rounds instead of n. (It also makes a good test of an engine: a buggy
semi-naive implementation misses derivations where *both* body literals
are new. See `test_nonlinear_recursion_joins_delta_with_new_facts`.)

**Mutual recursion.** Predicates can recurse through each other
(`programs/02-even-odd.dl` — run it with `--trace` to see both evaluated
in one stratum):

```prolog
odd(X, Y)  :- edge(X, Y).
odd(X, Y)  :- even(X, Z), edge(Z, Y).
even(X, Y) :- odd(X, Z), edge(Z, Y).
```

`odd`/`even` hold pairs connected by odd-/even-length paths. The engine
evaluates them together, in one fixpoint.

**A modern classic — pointer analysis.** Real static analyzers are
mutually recursive Datalog at heart. A miniature Andersen-style analysis
(`programs/02-points-to.dl`):

```prolog
pt(V, H)     :- alloc(V, H).                        % v = new h
pt(V, H)     :- assign(V, W), pt(W, H).             % v = w
hpt(H1, H2)  :- store(P, W), pt(P, H1), pt(W, H2).  % *p = w
pt(V, H2)    :- load(V, P), pt(P, H1), hpt(H1, H2). % v = *p
```

`pt` (variable points to heap object) and `hpt` (heap object's field
points to heap object) feed each other until the analysis stabilizes.


## Exercises

1. Write `same_component(X, Y)` for an *undirected* graph given directed
   `edge` facts. (Hint: you need edges both ways first.)
2. A bill of materials: `contains(bike, wheel). contains(wheel, spoke).`
   Write `has_part(X, Y)` at any depth, and count rounds with `--trace`
   for a chain of 6 parts.
3. Predict which of the three `path` variants takes the fewest rounds on
   a 16-node chain, then verify (`python3 benchmarks/generate.py chain 16`
   makes the input; compare `--trace` with and without `--naive` while
   you're there — the "tuples derived" column is naive evaluation paying
   for its lack of a delta).

Next: [negation](03-negation.md) — where "not" turns out to be the hard
part of the whole subject.
