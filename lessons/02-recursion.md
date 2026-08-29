# Lesson 2 — Recursion and semi-naive evaluation

The queries SQL historically couldn't ask are the recursive ones: *who are
all my ancestors? what can this function reach? which parts contain this
part, at any depth?* Recursion is where Datalog stops being a notation for
joins and becomes a language.

## Transitive closure

The canonical recursive program (`programs/reachability.dl`):

```prolog
path(X, Y) :- edge(X, Y).                 % base case
path(X, Z) :- edge(X, Y), path(Y, Z).     % recursive case
```

`path` is defined in terms of itself. Bottom-up evaluation handles this
naturally: paths of length 1 appear first, then length 2 (built from an
edge plus a length-1 path), and so on, until a round adds nothing new.

Termination is guaranteed: no rule can invent new constants, so there are
finitely many possible facts, and the fact set only grows. Every Datalog
program terminates. This is the deep trade against Prolog and general
logic programming, bought by banning function symbols.

## Watching it run

```sh
$ python3 datalog.py --trace programs/reachability.dl
Semi-naive evaluation:
  stratum 1 (path):
    round 1: +9 path
    round 2: +8 path
    round 3: +7 path
    ...
    round 8: no new facts — fixpoint
```

That last line deserves its word. A **fixpoint** of the rules is a
database they cannot grow: apply every rule to it and you get back
exactly what you already had. The trace's "no new facts" is the engine
discovering it has reached one — and because facts are only ever
added, the *first* fixpoint it reaches is the smallest one there is.

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
python3 datalog.py chain100.dl            # semi-naive: 0.22s
python3 datalog.py --naive chain100.dl    # naive:     10.7s
```

**48× on a hundred nodes**, and the gap widens with depth: naive
evaluation redoes every derivation in every round, so its total work
grows with rounds × relation size while semi-naive's grows with the
relation. Add `--trace` to either run to watch the mechanism —
semi-naive prints shrinking deltas, naive prints a "tuples derived"
count that climbs while the deltas shrink. That climbing number is
wasted work, quantified.

This one idea — track what changed, derive only its consequences — is the
ancestor of modern incremental view maintenance (Differential Dataflow,
DBSP).

## The same rules, on data you can't eyeball

`programs/reachability.dl` is a ten-node chain, which is good for
watching the machinery and bad for believing it matters.
`programs/supply-chain.dl` is the same two rules over a software
dependency graph: 160 packages, 292 dependency edges, 12 of them
services you deploy.

```prolog
uses(X, Y) :- depends(X, Y).
uses(X, Z) :- depends(X, Y), uses(Y, Z).
exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).
```

Two numbers make the case for recursion better than any chain does.
The 292 edges you *stated* imply **8,457** `uses` facts: the closure
is 29× the input, and the question "which services are exposed to this
CVE" is answered in the closure, not in the input. Four of the twelve
services are exposed, and nothing you can see in the file tells you
which four.

Now watch the deltas, because they do something the chain cannot:

```sh
$ python3 datalog.py --trace programs/supply-chain.dl
    round 1: +292 uses
    round 2: +475 uses
    round 3: +3 exposed, +661 uses
    round 4: +1 exposed, +838 uses
    round 5: +898 uses
    round 6: +908 uses
    round 7: +838 uses
    ...
    round 17: +4 uses
    round 18: no new facts — fixpoint
```

The frontier peaks at round 6, and that shape is the point. On a
chain the delta shrinks every round, because there is exactly one
new path length to find. On a real graph the frontier **expands first
and then collapses** — paths of length 6 are far more numerous than
paths of length 1 or length 16. That shape is what semi-naive is
exploiting: at round 6 it joins against 908 new facts instead of
re-deriving all 8,457 known ones.

The cost of not doing that is measurable:

```sh
$ python3 datalog.py --naive --trace programs/supply-chain.dl
```

Naive evaluation derives **166,171** tuples to arrive at the same 8,766
facts — nineteen times the work, all of it rediscovering things it
already knew. That ratio is the entire argument for the delta
discipline, and it grows with the graph.

## The mathematics underneath: a lattice and a fixpoint

The termination argument above deserves its proper names, because it
is the course's first load of real mathematics and the rest quietly
reuses it. Three definitions, then one theorem.

Since no rule invents constants, there are finitely many possible
facts. The **powerset** of that finite set is the collection of *all
its subsets* — every database you could ever be in the middle of
computing. Ordered by ⊆, the powerset forms a **lattice**: a partial
order where any two elements have a greatest lower bound and a least
upper bound (for fact-sets, plain intersection and union), with the
empty set at the bottom and "every possible fact" at the top.
Evaluation walks this lattice.

The walking is done by one function, the **immediate consequence
operator** `T_P`: feed it a set of facts, it returns everything
derivable from them in a single step (including, note, the facts'
own re-derivations). In these terms a **fixpoint** is a set `S` with
`T_P(S) = S` — the rules give back exactly what they were given — and
`T_P` is **monotone** if `S ⊆ S′` implies `T_P(S) ⊆ T_P(S′)`: growing
the input can only grow the output. Positive rules are monotone for a
one-line reason: a rule instance that fired against `S` still has all
its premises in the larger `S′`, so it fires again.

The **Knaster–Tarski theorem** says a monotone function on such a
lattice always has fixpoints, and among them a **least** one,
`lfp(T_P)`. Iterating from the bottom climbs to it: ∅ ⊆ T_P(∅) ⊆
T_P(T_P(∅)) ⊆ … is an ascending chain (each step is ⊆ the next, by
monotonicity), a finite lattice has no infinite ascending chains, so
the climb stops — and where it stops is the smallest set closed under
the rules. That least fixpoint *is* the meaning of a Datalog program;
naive and semi-naive are just two gaits for the same climb.

Monotonicity is the load-bearing word. `not` is precisely the thing
that breaks it — adding facts can *remove* conclusions — which is why
Lesson 3 has to rebuild the guarantee stratum by stratum, running this
argument once per layer. One theorem, applied as many times as the
program has strata.

## Two different sizes, two different curves

There is a distinction hiding in everything above, and naming it makes
the rest of the course legible. A Datalog program has two sizes — the
**rules** and the **data**, and cost behaves completely differently in
each.

Hold the program fixed (the two `path` rules) and grow the data:

```
   49 edge facts ->   0.07s
   99             ->   0.21s
  199             ->   1.38s
  399             ->  10.75s
```

Now hold the data fixed (40 facts over 12 nodes) and grow a single
rule, one body atom at a time:

```
   3-atom body ( 4 variables) ->   0.04s
   5-atom body ( 6 variables) ->   0.07s
   7-atom body ( 8 variables) ->   0.29s
   9-atom body (10 variables) ->   2.71s
  11-atom body (12 variables) ->  31.34s
```

Eight times the data cost 150×. Four more atoms in one rule cost 800×,
on data that never changed.

That is the shape of the two standard measures:

- **Data complexity** — program fixed, data varies. Datalog is
  **PTIME-complete** here (as hard as any problem solvable in polynomial
  time). Polynomial, and the exponent depends on the
  rules you wrote, not on how much data you have.
- **Combined complexity** — both vary. Datalog is
  **EXPTIME-complete** (exponential time), and the exponential lives in
  the number of
  variables per rule, because each one multiplies the space of
  candidate bindings to join over.

This is why "Datalog is polynomial" and "Datalog is exponential" are
both true and not in conflict, and it is the fact the whole field is
organised around. Real workloads have small programs and enormous data:
CodeQL runs a few hundred rules over a codebase with hundreds of
millions of facts, and it is only viable because the axis that grows is
the cheap one. It is also why Lesson 16 can call query minimisation
worth an NP-complete analysis: you pay it once per rule and save on
every row.

(This engine's data curve is worse than the theory allows: nested-loop
joins make it roughly cubic where an indexed engine would be closer to
quadratic. The *shape* is right, the constant is not — the *Under the
hood* section below shows the loops responsible.)

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
(`programs/even-odd.dl` — run it with `--trace` to see both evaluated
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
(`programs/points-to.dl`):

```prolog
pt(V, H)     :- alloc(V, H).                        % v = new h
pt(V, H)     :- assign(V, W), pt(W, H).             % v = w
hpt(H1, H2)  :- store(P, W), pt(P, H1), pt(W, H2).  % *p = w
pt(V, H2)    :- load(V, P), pt(P, H1), hpt(H1, H2). % v = *p
```

`pt` (variable points to heap object) and `hpt` (heap object's field
points to heap object) feed each other until the analysis stabilizes.


## Under the hood: the join, the delta, and the stamps

**The database is a dict of sets of tuples.** No storage engine, no
indexes: `rels["path"] == {("a","b"), ("a","c")}`. Matching an atom
against a tuple (`_match`) is one-way unification: variables take values
or must agree with earlier bindings. A rule body is evaluated by folding
`_match` over its literals under one growing substitution, which is
exactly a relational join, done as nested loops.

**Semi-naive is about twenty lines** (`Engine._eval_stratum`). Here it
is, so you do not have to open another window:

```python
    # Round 1: evaluate every rule of the stratum against the full db.
    delta = defaultdict(set)
    for rule in rules:
        for tup in self._produce(rule):
            if tup not in self.rels[rule.head.pred]:
                delta[rule.head.pred].add(tup)
    self._absorb(delta, stat)

    # Recursive rules: a positive body literal names a stratum predicate.
    recursive = []
    for rule in rules:
        occs = [i for i, lit in enumerate(rule.body)
                if not lit.negated and lit.atom.pred in preds]
        if occs:
            recursive.append((rule, occs))

    # Semi-naive rounds: substitute the previous round's delta into each
    # recursive position in turn; every other literal reads the full
    # (already-updated) relations, so no new derivation is missed and
    # nothing is recomputed from only-old facts.
    while delta:
        new_delta = defaultdict(set)
        for rule, occs in recursive:
            head = rule.head.pred
            for i in occs:
                if not delta.get(rule.body[i].atom.pred):
                    continue
                for tup in self._eval_rule(rule, delta_occ=i, delta=delta):
                    if tup not in self.rels[head]:
                        new_delta[head].add(tup)
        delta = new_delta
        self._absorb(delta, stat)
```

Round one
evaluates every rule against the full database. After that, each
recursive rule is re-evaluated once per recursive body position, with
that position restricted to the previous round's *delta* and every other
position reading the full (already-updated) relations. Why is that
complete? Any new derivation must use at least one new fact — put the
delta there; and because "full" already contains the delta,
delta-x-delta derivations are covered too (the non-linear `path` rule in
the tests exists precisely to catch engines that get this wrong).
Duplicates cost nothing: sets absorb them.

**Semi-naive is about twenty lines** (`Engine._eval_stratum`). Here it
is, so you do not have to open another window:

```python
    # Round 1: evaluate every rule of the stratum against the full db.
    delta = defaultdict(set)
    for rule in rules:
        for tup in self._produce(rule):
            if tup not in self.rels[rule.head.pred]:
                delta[rule.head.pred].add(tup)
    self._absorb(delta, stat)

    # Recursive rules: a positive body literal names a stratum predicate.
    recursive = []
    for rule in rules:
        occs = [i for i, lit in enumerate(rule.body)
                if not lit.negated and lit.atom.pred in preds]
        if occs:
            recursive.append((rule, occs))

    # Semi-naive rounds: substitute the previous round's delta into each
    # recursive position in turn; every other literal reads the full
    # (already-updated) relations, so no new derivation is missed and
    # nothing is recomputed from only-old facts.
    while delta:
        new_delta = defaultdict(set)
        for rule, occs in recursive:
            head = rule.head.pred
            for i in occs:
                if not delta.get(rule.body[i].atom.pred):
                    continue
                for tup in self._eval_rule(rule, delta_occ=i, delta=delta):
                    if tup not in self.rels[head]:
                        new_delta[head].add(tup)
        delta = new_delta
        self._absorb(delta, stat)
```

Round one
evaluates every rule against the full database. After that, each
recursive rule is re-evaluated once per recursive body position, with
that position restricted to the previous round's *delta* and every other
position reading the full (already-updated) relations. Why is that
complete? Any new derivation must use at least one new fact — put the
delta there; and because "full" already contains the delta,
delta-x-delta derivations are covered too (the non-linear `path` rule in
the tests exists precisely to catch engines that get this wrong).
Duplicates cost nothing: sets absorb them.

One more mechanism lives in this loop. As `_absorb` files each new
fact it records a `first_seen` stamp — the round-ordinal of its
arrival. `--explain` (Lesson 1) is built on nothing else: to justify a
fact, find a rule instance whose premises all carry *earlier* stamps
than the conclusion. Because facts only arrive when derivable from
what came before, such an instance always exists and the tree is
well-founded by construction — no cycle can justify itself. The same
machinery runs in reverse for *absent* facts: `--explain` on a fact
that is not derived walks each candidate rule's body and names the
first literal the join dies at (Lesson 17 puts it to work). And
`--trace` closes with two lines of accounting — each stratum's final
relation sizes, and the hottest rules with their share of the run —
which is usually all the profiling a slow program needs.

## Exercises

1. Write `same_component(X, Y)` for an *undirected* graph given directed
   `edge` facts. (Hint: you need edges both ways first.)
2. A bill of materials: `contains(bike, wheel). contains(wheel, spoke).`
   Write `has_part(X, Y)` at any depth, and count rounds with `--trace`
   for a chain of 6 parts.
3. Predict which of the three `path` variants takes the fewest rounds on
   a 16-node chain, then verify (`python3 benchmarks/generate.py chain 16`
   makes the input; compare `--trace` with and without `--naive` while
   you're there: the "tuples derived" column is naive evaluation paying
   for its lack of a delta).

4. Run `--naive --trace` beside the default on
   `programs/reachability.dl` and explain both number columns. Then
   read `_eval_stratum_naive` and name precisely what the semi-naive
   loop has that it lacks.
5. Add `max_rounds` protection to `Engine` and construct a program that
   would need it if function symbols were allowed. What stops you?
   (That is the point.)

Next: [negation](03-negation.md) — where "not" turns out to be the hard
part of the whole subject.
