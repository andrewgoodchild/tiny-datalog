# Lesson 18 — The neighbours

> **Entirely optional.** Nothing later depends on this lesson, because
> nothing comes later. The course compared Datalog to its neighbours
> in passing for seventeen lessons; this one collects the comparisons
> and finishes them — SQL, F-logic, functional programming, and the
> road not taken, category theory.

## SQL, the sibling that won

The nearest neighbour, and the one this course has been defining
itself against since lesson 0: Datalog is roughly SELECT–JOIN plus
real recursion, minus the ceremony. The two deep differences have both
already earned their own sections — recursion with a termination
theorem against `WITH RECURSIVE` with arithmetic and none (Lesson 14),
and what absence means. That second one deserves its full tour here,
because SQL's answer is a *presence that marks absence* — the null —
and "null" is not one concept.

- **SQL's NULL: one marker, at least three meanings.** *Unknown* (they
  have a phone, we don't know it), *inapplicable* (the fax column, for
  someone born in 2005), and *withheld* (they declined to say). Codd
  himself later argued one marker was a mistake and proposed splitting
  it into "applicable but unknown" and "inapplicable" — the industry
  kept the single NULL, plus a three-valued logic in which
  `NULL = NULL` is not true, `NOT IN` returns nothing if one null
  slips into the subquery, and `SUM` over no rows is NULL while
  `COUNT` is 0. Every one of those is a support ticket somewhere.
- **The labelled null: exists, unknown, but *self-identical*.** In
  database theory (incomplete databases, data exchange, the chase of
  Datalog±), "every person has a mother — someone" invents a
  placeholder witness. Unlike SQL's NULL, two occurrences of the same
  labelled null are *known equal*: an unknown individual, not an
  unknown value, and positive queries can treat it as an ordinary
  constant (the certain-answers story — Lesson 16's homomorphisms
  doing the work). This repository mints miniature ones: the `gen_N`
  names `subsumption.py` invents during normalisation are exactly
  this, Skolem constants with identity.
- **The null reference: absence as a crash.** Programming languages'
  `null`/`nil` is a pointer that goes nowhere — Tony Hoare called
  inventing it his "billion-dollar mistake". The modern fix, option
  types (`Maybe`, `Optional`), is the type system forcing the
  decomposition Datalog forces relationally: absence becomes a case
  you must handle, not a value that detonates on contact.

Sorted against Lesson 4's axis: Datalog's no-fact is closed-world
absence — it means false. SQL's NULL-as-unknown is an attempt to
smuggle one *open-world* cell into a closed-world table — the row
asserts the person exists while one column pleads ignorance — and the
three-valued logic is the bill for mixing the two assumptions in a
single relation. The labelled null is open-world absence done
honestly, with identity instead of a shrug.

## The road the rules camp took: F-logic

The description-logic line was not the frame tradition's only heir.
**F-logic** (Kifer and Lausen, 1989) folded frames into deductive
databases instead — objects with attributes as first-class syntax,
`bob : person[age -> 42]`, rules over all of it, even variables
ranging over attribute names. It looks higher-order and is not: a
molecule is sugar for `attr(bob, age, 42)` with `isa`/`sub` alongside,
and the object machinery is two bridge rules any reader of Lesson 2
can write. F-logic is to Datalog what objects are to relations — this
lesson's compile-to-Datalog thesis run in reverse — and where it
exceeds the core it lands on this course's own machinery: overridable
inheritance needs Lesson 5's well-founded semantics, and its flagship
implementation compiles to Lesson 15's tabling engine.

In the Semantic Web wars F-logic carried the closed-world rules camp;
OWL went to the description logics. The epilogue has a fine irony:
F-logic's *compilation target* — entity, attribute, value — is the
data model that won everywhere (RDF triples, Datomic's datoms). The
industry rejected the logic and adopted the encoding.

## The functional road: Haskell, and Datafun

Functional programming is the other declarative tradition, and the
kinship is real mathematics, not vibes. Both meanings live on
fixpoints: Lesson 2's `lfp(T_P)` on a lattice of fact-sets is the same
Kleene construction that gives a recursive function its meaning in
domain theory — iterate from bottom, take the limit. Both families
also made a deliberate trade around termination, in opposite
directions: Datalog restricted the language until every program halts;
Haskell kept Turing-completeness and bought back usable semantics with
laziness. And this course's algebra is a functional programmer's home
ground — a semiring is a typeclass, Lesson 8's evaluation is a fold
with `⊕` and `⊗` plugged in, and Lesson 13's lattices are exactly the
`join`-semilattice structures a Haskell library would abstract over.

The bridge is no longer hypothetical. **Datafun** (Arntzenius and
Krishnaswami, ICFP 2016) is a functional Datalog: a typed λ-calculus
in which the type system tracks *monotonicity*, so that fixpoints over
finite semilattices are guaranteed to exist for exactly Lesson 2's
reasons — the load-bearing property of this whole course, made a
static type. Read it after Lesson 13 and it is barely foreign.

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
containment — [Lesson 16](16-containment.md)), and **universal
algebra** (semirings and their quotients —
[Lesson 8](08-semirings.md)). Those are the tools the field actually
reaches for, and every result in these lessons is stated in them.

A reader arriving from category theory will notice that much of this
*can* be recast categorically: instances and homomorphisms form a
category, `lfp(T_P)` is an initial algebra, semiring specialisation is
a functor, and Lesson 6's coinductive subtyping — a greatest fixpoint
obtained as the complement of a least one — is the terminal coalgebra
sitting dual to Lesson 2's initial algebra. All true, and, for classical Datalog — none of it doing
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

0. Port the supply-chain query of Lesson 0 to `WITH RECURSIVE`. Which
   of the three properties from the README's opening survives the port
   verbatim, which survives with engine-specific caveats, and what did
   Lesson 14 say the arithmetic cost you?


1. Verify the recasting claim for one case: state `lfp(T_P)` as an
   initial algebra of a functor on sets of facts, then identify what
   the initiality property gives you that Lesson 2's Knaster–Tarski
   argument did not already give. (The honest answer is short.)
2. Lesson 16's canonical-instance trick — freeze a query's variables
   into constants — is an adjunction in disguise. Which two maps form
   the unit and counit, and between which categories?
3. Apply the criterion to something outside databases you know well.
   Find one problem in it that is genuinely about mappings between
   structures, and one that only *sounds* like it is, and say which
   side of the line each falls on and why.
