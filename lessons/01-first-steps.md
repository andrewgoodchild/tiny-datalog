# Lesson 1 — Facts, rules, and queries

Datalog is a database query language that looks like logic. A program has
two ingredients:

- **Facts** — the data. `parent(abe, bob).` says the relation `parent`
  contains the pair (abe, bob). Facts are what a database calls rows.
- **Rules** — the reasoning. `grandparent(X, Z) :- parent(X, Y), parent(Y, Z).`
  says: *for any* X, Y, Z, if X is a parent of Y and Y is a parent of Z,
  then X is a grandparent of Z. `:-` reads as "if"; the comma reads as
  "and".

Relations defined only by facts are called **EDB** (extensional — the
input); relations defined by rules are **IDB** (intensional — derived).

## A first program

This ships as `programs/01-family.dl` (with an `ancestor` rule you'll meet
properly in Lesson 2); the heart of it:

```prolog
parent(abe, bob).
parent(abe, ann).
parent(bob, carl).
parent(ann, dana).

grandparent(X, Z) :- parent(X, Y), parent(Y, Z).
sibling(X, Y) :- parent(P, X), parent(P, Y).
```

```sh
$ python3 datalog.py 01-family.dl
% grandparent/2 (derived) — 2 facts
grandparent(abe, carl).
grandparent(abe, dana).

% sibling/2 (derived) — ...
```

Two things to notice:

1. **Variables range over everything.** The engine finds *all* ways to
   match the body against the data. This is a join: `grandparent` is the
   relational join of `parent` with itself.
2. **`sibling` has a bug** — it derives `sibling(bob, bob)`, because
   nothing stops X and Y being the same person. Datalog has no `X != Y`
   built-in in this engine; the standard fix is to model the data so the
   issue can't arise, or filter afterwards. Sit with this example — being
   forced to notice what a rule *really* says is most of learning Datalog.

## Queries

```sh
$ python3 datalog.py -q 'grandparent(abe, X)' 01-family.dl
?- grandparent(abe, X)
   grandparent(abe, carl).
   grandparent(abe, dana).
   (2 answers)
```

A query is an atom with variables; the engine returns every match.
Constants in the query act as filters.

## Asking why

Any derived fact can be interrogated, from your very first program:

```sh
$ python3 datalog.py --explain 'grandparent(abe, carl)' programs/01-family.dl
?- explain grandparent(abe, carl)
   grandparent(abe, carl)   [via grandparent(X, Z) :- parent(X, Y), parent(Y, Z).]
     parent(abe, bob)   (base fact)
     parent(bob, carl)   (base fact)
```

The tree names the rule that fired and the facts it consumed, all the
way down to what you typed in. Two things make this different from an
explanation you would write by hand: it is generated from the same work
that produced the answer, so it cannot disagree with it, and it costs
nothing extra to ask.

Use it whenever a result surprises you — it is the fastest debugging
tool in the repository, and it gets more interesting as the programs
do (recursive derivations nest, and negated conditions are shown as
explicitly as positive ones). [Lesson 11](11-under-the-hood.md)
explains how it is built, once you have seen enough evaluation for the
mechanism to be interesting.

## How evaluation works (the short version)

The engine is **bottom-up**: it starts from the facts and applies every
rule in every possible way, adding new facts until nothing new appears —
the *fixpoint*. That's different from Prolog, which starts from a query
and searches top-down (and can loop forever; Datalog cannot — see the
next lesson).


## Exercises

1. Add `cousin(X, Y)` — two people whose parents are siblings. Does your
   rule accidentally make people their own cousins? Why?
2. Add `aunt_or_uncle(X, Y)`. You'll need a body with three literals.
3. Predict the output of `-q 'parent(X, carl)'` before running it.

Next: [recursion](02-recursion.md), where rules refer to themselves and
Datalog earns its keep.
