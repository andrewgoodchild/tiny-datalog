# Lesson 18 — The neighbours

> **Entirely optional.** Nothing later depends on this lesson, because
> nothing comes later. The course compared Datalog to its neighbours
> in passing for seventeen lessons; this one collects the comparisons
> and finishes them — SQL, F-logic, functional programming, and the
> road not taken, category theory.

## SQL, the sibling that won

The nearest neighbour, and the one this course has been defining
itself against since lesson 0: Datalog is roughly SELECT–JOIN plus
real recursion, minus the ceremony. But the two languages are not
strangers who happen to overlap — they are siblings with fifty years
of traffic between them, and the ledger of what crossed over, what
never did, and what each holds that the other cannot is the real
comparison.

**What crossed over.** More than recursion. A non-recursive Datalog
rule *is* a SQL view — same semantics, different clothes — and view
unfolding is rule unfolding. `WITH RECURSIVE` arrived in SQL:1999 from
the deductive-database line (Lesson 0's winter). The **magic sets**
rewriting of Lesson 7 is implemented inside IBM's DB2, quietly
optimising queries for people who have never heard the word Datalog.
And the optimizer equivalences every engine relies on rest on
conjunctive-query containment — Lesson 16's theorem, industrialised.

**What never made it, and should have.** SQL absorbed recursion's
*syntax* without its *semantics*. `WITH RECURSIVE` is defined
operationally — iterate this term, watch the bag grow — not as
Lesson 2's least fixpoint, and the differences leak: `UNION` versus
`UNION ALL` changes termination behaviour, mutual recursion is
unsupported by most engines, and each engine forbids negation and
aggregation over the recursive term in its own ad-hoc way. That last
restriction is stratification, arrived at by folklore — the theory
existed, and SQL absorbed the fence without the semantics that
justifies it. Set semantics lost too: SQL chose bags with `DISTINCT`
as an opt-in, and every accidental duplicate since has been the
interest on that loan.

**The honest ledger.** What SQL holds that Datalog does not: a type
system and schema DDL (Lesson 17's lament, solved decades ago);
arithmetic, strings and dates as first-class citizens (Lesson 14's
whole trade, paid and banked); `ORDER BY` and `LIMIT` — a Datalog
relation is a set, and *presentation order is not even expressible*;
outer joins; window functions; transactions and updates as part of the
language rather than a satellite module; and half a century of
optimizer engineering plus every developer already knowing it. What
Datalog holds: recursion that is native, uniform and terminating;
rules that compose the way views always wished they did; a principled
stratification discipline instead of per-engine folklore; and
derivations, provenance and incremental maintenance falling out of the
semantics rather than being bolted on.

Which leaves the deepest difference of all — what absence means. SQL's
answer is a *presence that marks absence*, the null, and "null" is not
one concept:

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
domain theory — iterate from bottom, take the limit.

The differences are just as structural, and worth a ledger of their
own:

- **Direction of computation.** Datalog saturates: compute *all*
  consequences bottom-up, then filter with a query. Haskell is
  demand-driven: laziness evaluates only what the result forces. The
  course has met both instincts converging — magic sets (Lesson 7) is
  bottom-up evaluation *discovering demand*, and tabling (Lesson 15)
  is top-down evaluation discovering memoisation. Haskell has both
  natively: laziness is demand, sharing is the table.
- **Relations against functions.** A function runs one way; a relation
  has no way. Lesson 14's `plus(X, Y, n4)` returning all five splits
  is unremarkable in Datalog and a party trick in Haskell — while
  function composition, the thing Haskell does with a dot, takes
  Datalog a fresh rule and a join.
- **The termination trade, made in opposite directions.** Datalog
  restricted the language until every program halts. Haskell kept
  Turing-completeness and bought back usable semantics with laziness —
  and its algebraic data types are precisely the function symbols
  Lesson 11 banned: `s(N)` refused by this parser is a perfectly
  ordinary Haskell constructor. One tradition fenced the infinite out;
  the other learned to compute with it unevaluated.
- **Who owns execution.** A Haskell program's performance is your
  program — you chose the folds and the data structures. A Datalog
  program's performance is the *engine's* choice: join order, indexes,
  magic sets, saturation strategy, all invisible to the rules. That is
  Datalog's deepest promise (the same rules, faster every engine
  release) and its deepest frustration (when the engine chooses badly,
  Lesson 17's guard-weaving is your only steering wheel).
- **Types.** Haskell's are the best in the business; Datalog's absence
  of them is Lesson 17's honest cost. There is no contest here, only a
  debt.

This course's algebra is a functional programmer's home ground
regardless — a semiring is a typeclass, Lesson 8's evaluation is a
fold with `⊕` and `⊗` plugged in, and Lesson 13's lattices are
`join`-semilattices a Haskell library would abstract over. And the
bridge is no longer hypothetical: **Datafun** (Arntzenius and
Krishnaswami, ICFP 2016) is a functional Datalog — a typed λ-calculus
whose type system tracks *monotonicity*, so that fixpoints over finite
semilattices are guaranteed to exist for exactly Lesson 2's reasons.
The load-bearing property of this whole course, made a static type.
Read it after Lesson 13 and it is barely foreign.

## Category theory

The last neighbour is not a language but a lens — the one this course
looked through, put down, and owes an explanation for. Category
theory, founded by Samuel Eilenberg and Saunders Mac Lane in 1945, is
the mathematics of *composition*. A **category** is almost
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
