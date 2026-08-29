# Lesson 16 — answers

**1. Minimising `q(X) :- e(X, Y), e(Y, Z), e(X, U), e(U, V).`**

Two atoms survive:

```sh
$ python3 containment.py --contains 'q(X) :- e(X, Y), e(Y, Z), e(X, U), e(U, V).' \
                         'q(X) :- e(X, Y), e(Y, Z).'
=> equivalent (each contains the other)
```

The body says "X starts a two-hop path" twice, in two sets of
variables. Either pair can be dropped — `minimise` happens to keep
`e(X, U), e(U, V)` because of the order it tries atoms in, and keeping
`e(X, Y), e(Y, Z)` instead would be equally correct. (The minimal form
is unique *up to renaming*, which is exactly what that ambiguity is.)

Not one atom, because `e(X, Y)` alone says only "X has an outgoing
edge"; it cannot guarantee a second hop, and no homomorphism can
manufacture one.

**2. The missing direction.**

The database `edge(a, b).` and nothing else. Then
`q(X) :- edge(X, Y).` returns `q(a)`, while
`q(X) :- edge(X, Y), edge(Y, X).` returns nothing, so the cycle query
does *not* contain the simple one. The homomorphism that fails is the
one from the cycle body into `{edge(X, Y)}`: sending `edge(Y, X)` onto
`edge(X, Y)` forces `Y ↦ X` and `X ↦ Y`, and X is a pinned head
variable. No map exists, and the theorem's verdict matches the
database's.

**3. Why head variables must be fixed.**

Without the pin, `q(X) :- edge(X, Y), edge(Y, X).` would "minimise" to
`q(X) :- edge(X, Y).`: the map X ↦ X, Y ↦ Y sends the first atom home,
and X ↦ Y, Y ↦ X sends the second, but those are different maps, and
a homomorphism must be *one* function. Fixing head variables is what
stops the optimiser from renaming the answer it was asked to return:
the query's output columns are not free to move. Drop the condition and
you would report `q(a)` on the database `edge(a, b).`, where the honest
answer is nothing.

**4. Where redundancy really comes from.**

Every shipped program is already minimal — people rarely hand-write a
redundant self-join. Redundancy is *generated*: inline a view into
another view and the same base atoms arrive by two routes; expand a
macro, unfold a rule, translate from SQL with overlapping subqueries,
or let magic sets rewrite a program (Lesson 7 adds a guard literal to
every rule — some of those are provably redundant on some rules).

Which is why an optimiser minimises **after** rewriting, not before:
the rewriting is what creates the work minimisation removes. Same
reason compilers run simplification passes after inlining rather than
in the source.

**5. Answering queries using views.**

(a) Both candidates are sound. Expanding r2 gives
`follows(X, Y), follows(Y, Z), follows(Z, W)` and

```
$ python3 containment.py --contains 'q(X, Z) :- follows(X, Y), follows(Y, Z).' 'q(X, Z) :- follows(X, Y), follows(Y, Z), follows(Z, W).'
=> outer contains inner, on every database
```

— the homomorphism maps q's two atoms onto the expansion's first two.
r1's expansion `follows(X, Y), follows(Y, X), follows(Y, Z),
follows(Z, Y)` certifies the same way.

(b) Run `--contains` with r2's expansion as outer and r1's as inner:
outer contains inner. The reason is visible in the atoms — r1's
expansion contains `follows(Z, Y)`, so Z follows someone, which is all
r2's trailing `follows(Z, W)` asks (send W to Y). Every answer r1 can
produce, r2 already produces; the union of candidates collapses to r2.

(c) `follows(a, b). follows(b, c).` — q answers (a, c), but c follows
nobody and nothing is mutual, so both views are empty and the
rewriting returns nothing. Maximal means *no sound view-only query
does better*, not *as good as having the data*: the views never
recorded the rows q needs, and no rewriting can conjure information
its sources never saw. That gap is the daily reality of data
integration, and the reason the field settled for maximally contained
rather than equivalent.
