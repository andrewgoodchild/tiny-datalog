# Lesson 26 — answers

Runnable candidates: `exercises/26-sg.candidates` (exercise 3).

**1. The ten rules of round 1.**

They are `r2`, `r3` and `r33`–`r40`: every candidate whose body uses
`parent` alone, except `r32`. With no `ancestor` fact yet derived, a
recursive rule has nothing to work on, so thirty candidates can be
switched on together and derive nothing; they cannot be the reason
`ancestor(ada, ben)` is missing. Any one of the ten produces a first
`ancestor` fact, and with the other thirty on (`r1` makes the relation
symmetric, `r6` transitive) that is enough to reach `ancestor(ada,
ben)`.

`r32` is `ancestor(X, Y) :- parent(X, Y), parent(Y, X).` It never
fires: nobody in a family tree is their own parent's parent. It was
switched on without effect, so it is not on the list. Note that the
clause comes from running the rules on *this* data, not from reading
them.

**2. `--max-body 1`.**

```sh
$ python3 synthesis.py programs/kinship.dl --examples programs/ancestor-sparse.examples --max-body 1
3 candidate rules: bodies of up to 1 atom, 1 extra variable
2 rounds, 2 constraints, 8 evaluations
no subset of the candidates fits the examples: widen the candidates (--max-body, --vars, --candidates), or check the examples
```

It proves that none of the eight subsets of those three rules derives
all six positive examples and none of the negative ones. It proves
nothing about `ancestor`: the next size up contains the answer. An
"unsatisfiable" from this loop is always a statement about the
candidate list.

**3. Same-generation without `r7`.**

```sh
$ python3 synthesis.py programs/kinship.dl --examples programs/sg.examples --candidates exercises/26-sg.candidates
8 candidate rules from exercises/26-sg.candidates
8 rounds, 15 constraints, 64 evaluations
no subset of the candidates fits the examples: widen the candidates (--max-body, --vars, --candidates), or check the examples
```

No subset fits. With `-t`, round 3 reports
`missing sg(dov, fay): require one of {r8}`, where `r8` is now
`sg(X, Y) :- parent(P, X), sg(P, Y).` A clause with one rule in it
says that rule is *necessary*: every solution contains it. That
halves the space in one step, and the solver never proposes a subset
without it again. Here it is also the beginning of the end, because
`r8` derives wrong answers with every partner that could supply the
rest, and the why-clauses say so one by one.

**4. Why no `not`.**

```prolog
p(X) :- q(X), not r(X).      % rule 1
r(X) :- q(X).                % rule 2
```

With `q(a)` and only rule 1 on, `p(a)` holds. Switch rule 2 on and
`p(a)` is gone. Both kinds of constraint depend on that never
happening. A why-clause forbids a set of rules because every larger
set derives the same wrong answer; here a larger set might not. A
why-not clause requires one of the rules left off because every
smaller set also misses the answer, and it grows the failing set on
the assumption that an answer once derived stays derived. With
negation the loop would learn clauses that rule out correct programs.

**5. Which recursion, and why.**

FOIL's rule is `r29`, printed with its atoms in the candidates'
alphabetical order: `ancestor(X, Y) :- ancestor(Z, Y), parent(X, Z).`
This lesson's is `r6`.

The solver sets the highest-numbered undecided rule *off* first. So
when a clause says "one of {r5, r6, r9, r10, ..., r29, r31}", every
rule in it is switched off in turn from the top until only the
lowest-numbered is left, and that one is forced on. Round 3 therefore
tried `r5`, learned that `r2` and `r5` together are forbidden, and
round 5 took the next lowest, `r6`, which worked. `r29` would have
worked too, as would `r10`; the loop stops at the first program that
fits. Which of several correct programs you get is an accident of
numbering, which is one more reason to validate what comes out.
