# Lesson 11 — answers

**1. The two `--trace` columns, and what naive lacks.**

The delta column (`+9 path`) counts facts that are *new* this round;
the naive-mode column (`(24 tuples derived)`) counts every derivation
performed, new or not — and it grows each round while the deltas
shrink, because naive evaluation rederives the entire relation-so-far
every time. What `_eval_stratum_naive` lacks is one thing: the
restriction of one body position to the previous round's delta
(`_eval_rule(delta_occ=i, delta=...)`) — the single argument-pair that
is the whole of semi-naive.

**2. Adding `X != Y`.**

The sketch (deliberately not merged — it's your exercise): a `neq`
token or reserved predicate in the parser; a safety rule that both
arguments must be bound by earlier positive literals (an unbound
disequality would mean "for some value they differ" — always true — or
force enumeration of an open domain); and evaluation as a filter in
`_rule_substitutions`, exactly where negated literals filter. Note the
order sensitivity you must handle: the check can only run once both
variables are bound, which is why real engines treat built-ins as a
scheduling problem — the README's "Deliberately missing" section is
this exercise's design discussion.

**3. `max_rounds` protection for `Engine`.**

You can add the parameter, but no Datalog program can ever need it:
finitely many constants → finitely many possible facts → a monotone
loop must stop. To *need* the guard you'd have to invent new values
mid-derivation — function symbols — and `validate` refuses them before
evaluation starts. The exercise's answer is the proof pattern:
termination lives in the language definition, not the loop.

**4. Hand-simulating the magic rewriting of `ancestor(bob, X)`.**

```prolog
ancestor#bf(X, Y) :- magic#ancestor#bf(X), parent(X, Y).
magic#ancestor#bf(Y) :- magic#ancestor#bf(X), parent(X, Y).
ancestor#bf(X, Z) :- magic#ancestor#bf(X), parent(X, Y), ancestor#bf(Y, Z).
magic#ancestor#bf(bob).
```

Evaluation: magic = {bob, carl} (the demanded start points), then
`ancestor#bf(bob, carl)` and nothing else — 3 IDB facts where full
evaluation derives 14. Check against `--magic --trace`.
