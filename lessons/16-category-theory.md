# Lesson 16 — The road not taken: category theory

> **Entirely optional.** Nothing later depends on this lesson, because
> nothing comes later. It exists for one kind of reader: the one who
> arrives knowing some category theory and suspects this whole course
> could have been written in it.

## What category theory is

Founded by Samuel Eilenberg and Saunders Mac Lane in 1945, category
theory is the mathematics of *composition*. A **category** is almost
embarrassingly little: a collection of **objects**, a collection of
**arrows** between them (each with a source and a target), a rule for
composing arrows that meet end-to-end, an identity arrow on every
object — and two laws, associativity and identity. That is the whole
definition.

The discipline is in what you give up: you may never look *inside* an
object. Everything must be said in terms of arrows and how they
compose. Sets-with-functions form a category; so do database schemas
with mappings, program types with functions, and proofs with
deductions — and any statement made arrow-only transfers to all of
them at once. That is the power (theorems for free, across fields) and
the famous danger (practitioners call it "abstract nonsense", a
nickname worn with pride): the vocabulary applies to everything,
which makes it easy to *describe* something categorically without
*gaining* anything. This lesson is about telling those two cases
apart.

## What the course is actually made of

The course's mathematics is **lattice theory** (fixpoints —
[Lesson 2](02-recursion.md)), **model theory** (homomorphisms and
containment — [Lesson 14](14-containment.md)), and **universal
algebra** (semirings and their quotients —
[Lesson 7](07-semirings.md)). Those are the tools the field actually
reaches for, and every result in these lessons is stated in them.

A reader arriving from category theory will notice that much of this
*can* be recast categorically: instances and homomorphisms form a
category, `lfp(T_P)` is an initial algebra, semiring specialisation is
a functor. All true, and, for classical Datalog — none of it doing
work the lattice-and-semiring toolkit wasn't already doing. Nothing in
`datalog.py` would be different. It is worth saying plainly, because
the vocabulary is attractive enough to mistake for content.

## Where the machinery earns its place

It is one step outside this repository, and it is worth seeing *why*,
because it sharpens the point above into a criterion. The
**Categorical Query Language** (CQL — Spivak and Wisnesky, the Topos
Institute line) takes "a schema is a graph" literally and then
further: a schema is a *category*, with foreign keys as morphisms and
integrity constraints as path equations, and a database instance is a
*functor* from it into sets — so an instance violating a constraint is
not a bad database, it fails to be an instance at all. The payoff is
**migration**: a mapping between schemas is a functor, and general
theory hands you three migration operators (Δ pulls data back; its
adjoints Σ and Π are principled merge and join, as Kan extensions).
Merging two databases with Σ is constraint-preserving *by
construction* — a guarantee an ETL script cannot make and relational
algebra does not offer.

There is the criterion: **category theory pays rent when the problem
is mappings *between* structures.** Migrating data across schemas is
exactly that; evaluating rules inside one schema is not, which is why
the recasting above does no work and this does.

The same boundary holds for **existential rules** (Datalog±), where
the chase — the procedure CQL's Σ is computed by — is a left Kan
extension. Both concern the fragment this engine deliberately does not
implement, and both are live research rather than settled technique.
If you add existentials, that is the road; until then, it is a
signpost.

## Exercises

1. Verify the recasting claim for one case: state `lfp(T_P)` as an
   initial algebra of a functor on sets of facts, then identify what
   the initiality property gives you that Lesson 2's Knaster–Tarski
   argument did not already give. (The honest answer is short.)
2. Lesson 14's canonical-instance trick — freeze a query's variables
   into constants — is an adjunction in disguise. Which two maps form
   the unit and counit, and between which categories?
3. Apply the criterion to something outside databases you know well.
   Find one problem in it that is genuinely about mappings between
   structures, and one that only *sounds* like it is, and say which
   side of the line each falls on and why.
