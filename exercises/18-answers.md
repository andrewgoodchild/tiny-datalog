# Lesson 18 — answers

Runnable theory (exercises 1 and 3): `exercises/18-answers.dfl`.

**1. A guarantor rule.**

```prolog
r5: member(P), guaranteed(P) => may_borrow(P).
r5 > r2.     % a guarantor answers an overdue loan...
r4 > r5.     % ...but not a suspension
```

```
$ python3 defeasible.py -q 'may_borrow(P)' exercises/18-answers.dfl
?- may_borrow(P)
   may_borrow(iris)             +∂
   may_borrow(jon)              −∂
   may_borrow(kim)              −∂
   may_borrow(lena)             +∂
   may_borrow(mo)               +∂
```

Mo has an overdue book and a guarantor, and borrows. `r2` attacks him
and `r5` beats it. Kim also has a guarantor, but `r4 > r5` keeps the
suspension on top. Forget that line and Kim comes out −∂ both ways,
the same signature as Jon in the lesson's draft. Two priorities are
needed, not one, because a new rule enters the order at two places:
what it beats, and what beats it.

**2. Remove `r4 > r3`.**

Only Kim changes. `r3` (staff) and `r4` (suspended) now both fire for
her, and neither outranks the other. So `may_borrow(kim)` and
`~may_borrow(kim)` are both −∂. That is not *undecided*. −∂ both ways
is a conflict, which the logic detects and refuses to resolve: it is
proved that neither side can be established. Undecided means neither
+∂ nor −∂ could be proved at all, which takes a loop (the lesson's
`programs/loops.dfl`). The first is a question for the policy's owner.
The second is a question about the theory's structure.

**3. Nixon's diamond, and downstream.**

```
$ python3 defeasible.py -q 'hawk(X)' exercises/18-answers.dfl
?- hawk(X)
   hawk(nixon)                  +∂
```

```
$ python3 defeasible.py --propagating -q 'hawk(X)' exercises/18-answers.dfl
?- hawk(X)
   hawk(nixon)                  −∂
```

`pacifist(nixon)` and `~pacifist(nixon)` are −∂ under both policies:
the diamond is a conflict with no priority. The difference is
downstream. `n4: pacifist(X) => ~hawk(X)` attacks `hawk(nixon)`. Under
blocking, `n4` is dead because its body is not proved, so the hawk
conclusion stands. Under propagating, `n4` is live because its body is
*supported*, and the conclusion falls. Which answer is right depends
on what acting on a contested premise costs, which is the lesson's
point.

**4. The checklist, revisited.**

- **Well-formed?** Still mechanical. The parser and the grounding
  report unsafe rules, unknown labels, and a cyclic superiority order.
- **Circular?** The question changes. Nothing is rejected for being
  circular. Instead, look for *undecided* literals: those are the
  loops the logic could not settle.
- **Exactly one answer?** Always, by construction, since the logic is
  sceptical and computes one set of conclusions. The question it
  replaces is "anything −∂ both ways?", which is a conflict nobody
  ranked.
- **Any rule doing no work?** Still a person's job. A rule beaten by
  everything that could fire alongside it is dead code, and nothing
  here reports it.
- **Does the reason read correctly?** Still a person's job, and harder
  than in Lesson 17: the module has no `--explain`, so the reason for a
  conclusion is the proof conditions applied by hand.

The logic answers the structural questions for you. It does not tell
you whether the priorities match the regulation. As in Lesson 17, that
remains the reviewer's job.
