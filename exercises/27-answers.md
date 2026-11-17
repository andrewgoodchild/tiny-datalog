# Lesson 27 — answers

Runnable program: `exercises/27-sibling.dl` (exercise 5).

**1. Draft 2, from the expectations file.**

The verdict is the same: one wrong answer, `may_borrow(kim)`, and the
rule at fault is `may_borrow(P) :- staff(P).` The oracle needs nothing
more because the rule's only premise is `staff(kim)`, a stated fact,
and the data is taken as given. There is no derived premise to be in
doubt about, so there is no "unless".

**2. A longer chain, and a refused symptom.**

```sh
$ python3 diagnose.py programs/access-draft.dl --against programs/access.dl --wrong 'allowed(alice, delete, company)'
   allowed(alice, delete, company) should not hold   [via allowed(U, A, O) :- can(U, A, O), hr_feed_current, not suspended(U).]
     can(alice, delete, company) should not hold   [via can(U, delete, O) :- user(U), has(U, owner, O).]
       has(alice, owner, company) should not hold   [via has(U, R, F) :- parent(O, F), has(U, R, O).]
         has(alice, owner, eng_folder) should not hold   [via has(U, R, F) :- parent(O, F), has(U, R, O).]
   => the rule at fault: has(U, R, F) :- parent(O, F), has(U, R, O).
```

The `allowed` rule joins the top of the chain. It is not blamed
because one of its premises, `can(alice, delete, company)`, is itself
wrong, and a rule is only at fault when every premise is right. Its
other premises (`hr_feed_current`, and `not suspended(alice)`) are
fine, and the search does not need to look at them once it has found
a wrong one.

`--wrong 'can(alice, view, company)'` is refused:
`can(alice, view, company) is called wrong, but programs/access.dl
derives it`. Alice is in eng, eng is in staff, and staff may view the
company folder, so that answer is right, in the draft and in the
reference. A symptom that contradicts the oracle is a mistake in the
question.

**3. Divide and query.**

Ask about the fact in the middle of the chain. If the oracle says it
is wrong, the culprit is at or below it: discard everything above. If
it is right, treat it as if it were a stated fact and discard
everything below. Either way half the chain is gone, so 400 steps
take about nine questions (log2 400 ≈ 8.6) where top-down takes up to
400.

Both discards are sound without assuming anything about the facts in
between. A wrong fact always has a culprit in its own derivation:
follow wrong premises down, and since the stated facts at the bottom
are right, the descent must stop at a rule with right premises and a
wrong conclusion. And a right fact can be cut off because the culprit
search only ever descends through *wrong* premises. What halving does
not need is for wrongness to be "monotone" along the chain, and it is
not: a wrong premise can support a conclusion that happens to be
right.

**4. Facts that would expose the two silent mutants.**

For the `user(U)` guard, let a group own something:

```sh
$ python3 datalog.py --assume 'grant(payroll, owner, eng).' -q 'can(eng, delete, O)' programs/access.dl
?- can(eng, delete, O)
   (0 answers)
```

The original answers nothing; the mutant, with `user(U)` dropped,
would answer `can(eng, delete, payroll)`. No new expectation is
needed: `:- can(eng, A, O).` is already in `programs/access.expect`,
and was powerless only because no group owned anything.

For `hr_feed_current`, take the feed away:

```sh
$ python3 datalog.py --assume 'hr_feed_current~.' -q 'allowed(alice, delete, O)' programs/access.dl
?- allowed(alice, delete, O)
   (0 answers)
```

The original allows nothing, which is the point of failing closed;
the mutant would allow `allowed(alice, delete, roadmap)`. The
expectation to write for that database is `:- allowed(U, A, O).`

Both fixes are a second test database, not a second expectation. A
rule set with a switch in it needs data for each position of the
switch.

**5. A comparison mutant is never "equivalent".**

```sh
$ python3 mutation.py exercises/27-sibling.dl
4 rules, tested by 0 constraints and 0 expectations
17 mutants: 0 killed, 17 survived, 0 equivalent   (score 0%)
```

With `-v` the list includes

```
  comparison    sibling(X, Y) :- parent(P, X), parent(P, Y), X != Y.
            ->  sibling(X, Y) :- parent(P, X), parent(P, Y), X = Y.
```

which is certainly not equivalent, and would be reported as a
survivor even if it were. `proved_same` asks `containment.contains`,
which refuses any rule with a comparison: Chandra–Merlin is a result
about conjunctive queries, and with comparisons one homomorphism is
no longer enough (lesson 16, and Klug's theorem in its code). So the
equivalence check quietly applies only to the fragment where it is a
theorem, and everything else is left for a person. The same goes for
`not` and for aggregates.

**6. A second family.**

With `parent(zed, yan).` added, the learned rules give `sg(zed, zed)`
and `sg(yan, yan)` and nothing connecting the two families: `sg(yan,
ben)` is not derived. Yan and Ben are each one step below the top of
their own family, so by the description "the same number of steps
down" they are the same generation, and the rules say otherwise. The
recursion only ever relates people who share an ancestor.

Is that wrong? The examples cannot say. All 23 were about Ada's
family, and the closed world was drawn over nine people who all
descend from her. Both readings fit every example.

None of the lesson's tools would have warned. `diagnose.py` checks
expectations, and there is none about Yan. `mutation.py` measures
whether the tests pin the rules down on the facts provided, and on
those facts they do. This is lesson 17's second failure mode, "rules
that are coherent and wrong", arriving by a new route: a learner
makes it easier to end up with rules nobody has read. The remedy is
the old one. Somebody who knows what "same generation" is for has to
be asked about a case the examples did not cover.
