# Lesson 14 — answers

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
edge" — it cannot guarantee a second hop, and no homomorphism can
manufacture one.

**2. The missing direction.**

The database `edge(a, b).` and nothing else. Then
`q(X) :- edge(X, Y).` returns `q(a)`, while
`q(X) :- edge(X, Y), edge(Y, X).` returns nothing — so the cycle query
does *not* contain the simple one. The homomorphism that fails is the
one from the cycle body into `{edge(X, Y)}`: sending `edge(Y, X)` onto
`edge(X, Y)` forces `Y ↦ X` and `X ↦ Y`, and X is a pinned head
variable. No map exists, and the theorem's verdict matches the
database's.

**3. Why head variables must be fixed.**

Without the pin, `q(X) :- edge(X, Y), edge(Y, X).` would "minimise" to
`q(X) :- edge(X, Y).`: the map X ↦ X, Y ↦ Y sends the first atom home,
and X ↦ Y, Y ↦ X sends the second — but those are different maps, and
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
or let magic sets rewrite a program (Lesson 4 adds a guard literal to
every rule — some of those are provably redundant on some rules).

Which is why an optimiser minimises **after** rewriting, not before:
the rewriting is what creates the work minimisation removes. Same
reason compilers run simplification passes after inlining rather than
in the source.
