# Lesson 21 — answers

Runnable rules: `exercises/21-answers.dl` (exercises 2 and 3).

**1. A Robot after all.**

Add `alloc(d, h6). heap_type(h6, robot). vcall(s3, d, speak, z).` and
`calls(S, M)` gains exactly one edge, `calls(s3, robot_speak)`, while
`pt(z, H)` is `{h5}`, the `Gear` that `Robot.speak` returns. `s1` and
`s2` are unchanged: a new allocation affects only the call sites its
object can reach, which is the precision CHA never had. The other
thing to notice is what you did *not* do: you did not re-run a
call-graph phase and then a points-to phase. One fixpoint absorbed
both changes.

**2. One call site of context.**

```prolog
tainted_in(top, V) :- source(V).
tainted_in(S, F)   :- call(S, M), actual(S, A), formal(M, F),
                      tainted_in(top, A).                     % in, per site
tainted_in(top, R) :- call(S, M), returns(M, X), result(S, R),
                      tainted_in(S, X).                       % out, same site

finding(S, V) :- sink(S, V), tainted_in(top, V).
```

`finding` is now just `sink1`. `tainted_in(C, p)` holds only for
`c1`: the parameter is tainted *when id is called from c1*, and the
return rule requires the same site `S` going out as coming in, which
is the whole fix. `k` comes out of `id` at `c2`, where `p` was never
tainted.

This answer only tracks callee variables per site and the caller's in
`top`, which is enough for one level of calls. A callee that calls
another function needs contexts that are sequences of sites (k-CFA
with k > 1), and Datalog without function symbols cannot build
unbounded sequences. Real analyses bound k, and the bound is the
precision-for-termination trade lesson 11 drew, inside one analysis.

**3. Reaching definitions.**

```prolog
kills(N, D) :- def(D, V, _), def(D2, V, N), not same_def(D, D2).
same_def(D, D) :- def(D, _, _).
reaches(D, N) :- def(D, _, P), succ(P, N).                       % leaves its node
reaches(D, N) :- reaches(D, P), succ(P, N), not kills(P, D).     % ...and survives
```

On the four-node example both definitions of `x` reach `n4`: `d1`
along the branch around `n3`, and `d2` from `n3` itself. `d1` cannot
survive *through* `n3`, which kills it. The `not` is legal by lesson
3's discipline: `kills` depends only on `def`, so it sits in a stratum
below `reaches` and is finished before `reaches` consults it. (The
`same_def` trick is the engine-without-`!=` way to say "a different
definition of the same variable": lesson 14, exercise 4.)

**4. Demand on the taint program.**

`--magic` derives 15 facts against 10 under full evaluation. It
costs facts. Everything in this program is relevant to `sink1`: the
source, both calls to `id`, the flows. So demand prunes nothing, and
the magic predicates are pure overhead. That is lesson 7's rule, *magic
sets pays in proportion to how much the query's bindings prune the
search*, in its losing case. On a million-line program with one sink
you care about, almost nothing is relevant, and demand-driven analysis
is the difference between analysing the program and analysing the
neighbourhood of one call. That is why on-demand points-to analysis is
a research area of its own, and why tabled engines (lesson 15) have
been used to run analyses goal-first.

**5. Must-analyses.**

"Is this variable definitely initialised on *every* path to here?"
"Is this lock held on *every* path to this call?" Each is a
universal statement over paths, and Datalog derives only existential
ones. Lesson 6's move applies directly: derive the **counterexample**,
"there is a path to here on which the variable is not initialised"
(an ordinary reachability rule), and negate it one stratum up.
`definitely_init(V, N) :- node(N), var(V), not maybe_uninit(V, N).`
The may-analysis computes the existential, and the must-analysis is
its complement.
