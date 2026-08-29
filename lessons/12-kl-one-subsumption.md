# Lesson 12 — KL-ONE and subsumption: reasoning about definitions

Everything so far reasoned about *facts*: which tuples are in which
relations. This lesson's question is one level up: what follows from
**definitions themselves**? If a Father is "a man with a child", and a
Parent is "a person with a child", then every father is a parent — no
data required. That inference is called **subsumption**, and the system
that made it famous is KL-ONE.

## KL-ONE and the classifier

KL-ONE grew out of Ron Brachman's 1977 Harvard thesis, which took the
era's "semantic networks" apart — diagrams of nodes and arrows whose
meaning lived mostly in the reader — and asked what the arrows
actually *meant*. The system he then built at BBN (the usual gloss of
the name is "Knowledge Language One", and the ONE was earnest: the
successors were literally numbered and initialled — NIKL, the "New
Implementation of KL-ONE", then KL-TWO, KRYPTON, LOOM, and CLASSIC at
AT&T) reorganised networks and frames into something with actual
semantics: **concepts**
with structured definitions built from other concepts and **roles**
(relations). Its celebrated feature was the *classifier* — assert a new
concept's definition and the system computes, automatically, where it
belongs in the hierarchy. The reasoning service underneath:

> C is **subsumed** by D (written C ⊑ D) iff every possible instance of
> C must be an instance of D, in every world consistent with the
> definitions.

Note what changed from the last ten lessons: this is *terminological*
reasoning (a "TBox," about concepts), not *assertional* reasoning (an
"ABox," about individuals). Datalog answers "which tuples?"; subsumption
answers "which definitions entail which?"

## Ontologies, and why anyone pays for one

KL-ONE's descendants converged on a word borrowed from philosophy:
**ontology** — from the Greek for the study of *what exists*. In
knowledge engineering it means something narrower and more useful: a
formal, shared specification of a domain's concepts and how they
relate, precise enough for a machine to check. Tom Gruber's 1993
definition is the one everybody quotes: *an explicit specification of
a conceptualization*.

The unglamorous reason ontologies matter is **agreement**. Two systems
can exchange data only if they mean the same thing by the same terms,
and an ontology is that agreement written down, machine-checkable, and
maintained in one place instead of re-negotiated in every interface.
The evidence is the deployments:

- **SNOMED CT** (this lesson's destination): ~350,000 clinical
  concepts behind electronic health records, so that "myocardial
  infarction" recorded in one hospital is the same concept queried in
  another — and classified by exactly the saturation calculus this
  lesson compiles to Datalog.
- **The Gene Ontology**: molecular biology's shared vocabulary for
  gene function, used to annotate genomes across species — the reason
  a yeast result and a human result can be compared at all.
- **schema.org**: the search engines' joint vocabulary for marking up
  web pages, probably the widest-deployed ontology in existence, if
  also the shallowest.

The classifier is what makes ontologies at this scale *maintainable*.
Nobody hand-curates 350,000 concepts into a correct hierarchy; you
write definitions and let subsumption compute where each belongs, and
recompute after every edit. That is also the cautionary tale's moral:
the grand projects that tried to encode everything by hand — Cyc,
running since 1984, is the famous one — found that the encoding, not
the reasoning, is the expensive part.

Which is why the idea is current again. The division of labour this
repository's README argues for — let a language model draft, let an
engine check — is exactly the shape of modern ontology work: extraction
is cheap now, and the classifier is the verifier that keeps the
extracted terminology coherent.

The fragment this lesson implements is **EL**: conjunction (`and`) and
existential restriction (`some`), nothing else. Subsumption in EL is
polynomial, and EL is no toy: it is the tractable core underneath the
OWL 2 EL profile, the family that reasoners like ELK and Snorocket
scale to SNOMED CT, the ~350,000-concept clinical terminology used in
health records worldwide. Why *this* fragment of all fragments — and
how close the field came to betting on the opposite one — is the
tradeoff saga near the end of the lesson; first, the machinery.

## The punchline: subsumption compiles to Datalog

EL subsumption is decided by a *saturation calculus*: normalise the
ontology into four axiom shapes, then apply completion rules to fixpoint.
Monotone rules, run to fixpoint, that is, a Datalog program. So this
repository's implementation (`subsumption.py`) is a **compiler**: it
normalises the ontology, emits facts plus seven rules, and hands them to
the engine you already know. Here are the seven, verbatim from `--emit`
(the program runs under plain `datalog.py`):

```prolog
subs(C, C) :- concept(C).
subs(C, E) :- subs(C, D), isa1(D, E).
subs(C, E) :- subs(C, D1), subs(C, D2), isa2(D1, D2, E).
link(C, R, E) :- subs(C, D), isa_some(D, R, E).
subs(C, E) :- link(C, R, D), subs(D, Dp), some_isa(R, Dp, E).
subs(C, E) :- subs(C, bot), concept(E).
subs(C, bot) :- link(C, R, D), subs(D, bot).
```

Read the first five as the EL calculus: everything subsumes itself;
follow a stated inclusion; combine two subsumptions through a
conjunction; propagate a subsumption into an existential (`link`
records "C reaches E through role R"); and discharge an existential
appearing on the right of an inclusion. The last two — call them CR5
and CR6 — carry disjointness: ⊥ sits below everything, and an
existential whose filler is impossible is itself impossible. That block *is* KL-ONE's classifier — the whole reasoning
service, in the language of Lessons 1–3. When a problem's inference
rules are monotone, "compile it to Datalog" is a general-purpose trick,
and this is what it looks like done.

The ontology (`programs/family-ontology.dl` — note it uses the
compound terms Datalog itself forbids; the ontology language *needs* the
structure Datalog banned, which is why it must be compiled):

```prolog
isa(man, person).
isa(woman, person).
define(parent,      and(person, some(has_child, person))).
define(father,      and(man,    some(has_child, person))).
define(mother,      and(woman,  some(has_child, person))).
define(grandfather, and(man,    some(has_child, parent))).
```

`isa` states a necessary condition (a *primitive* concept, in KL-ONE
terms); `define` states necessary **and sufficient** conditions — and
only defined concepts can be discovered to lie under things you never
said. Run the classifier:

```
$ python3 subsumption.py programs/family-ontology.dl
Classification (7 named concepts):
  father         ⊑  man, parent*
  grandfather    ⊑  father*
  man            ⊑  person
  mother         ⊑  parent*, woman
  parent         ⊑  person
  person         (top of hierarchy)
  woman          ⊑  person
  (* = inferred by the classifier, not stated)
```

Three subsumptions nobody stated: every father is a parent, every mother
is a parent, and every grandfather is a *father* (having a child who is
a parent is, in particular, having a child who is a person). That
asterisked discovery is KL-ONE's party trick, reproduced by seven
Datalog rules.

Two details worth reading in `subsumption.py`: normalisation mints fresh
names (`gen_1`, ...) for nested expressions, choosing the inclusion's
direction by which side of ⊑ the expression sits on: a conservative
extension, and essentially the structural normalisation KL-ONE performed;
and the completion rules in `datalog()` are the CR1–CR6 calculus
that industrial EL reasoners (ELK, Snorocket) implement with exactly the
optimisations this course already taught: saturation is semi-naive
fixpoint, and goal-directed subsumption checks are magic sets.


## Two evaluators, one calculus

The compilation is the pedagogy; it is not how production reasoners
run. ELK and Snorocket implement the same completion rules as
specialised saturation — indexed worklists instead of nested-loop
joins — and `subsumption.py` now carries both: `classify()` hands the
compiled program to the engine, `classify(fast=True)` (CLI `--fast`)
runs the identical CR1–CR6 calculus natively, and the tests hold the
two equal on every ontology they touch, unsatisfiability included.

The gap is worth measuring rather than asserting. The benchmark
generator grows ontologies:

```sh
$ python3 benchmarks/generate.py ontology 300 > /tmp/ont300.dl
```

The classifier now prints its own time, so the claim is the tool's,
not this paragraph's: on those 300 chained definitions the compiled
path reports about 4 seconds and `--fast` about 2 milliseconds — three
orders of magnitude, and the gap grows with size. (Time the whole
*process* and you will see nearer 60×: once the reasoner costs
milliseconds, interpreter startup and parsing dominate the wall clock
— itself a lesson about what to measure.) Nothing semantic separates
the two paths; the difference is Lesson 7's indexing tax paid once per
join versus data structures built for exactly these rule shapes. That is the whole
story of every "compiled to Datalog" system in miniature: the
compilation buys you semantics, cross-checking and a free evaluator on
day one, and when the day comes that speed matters, the calculus is
already the specification the fast implementation is tested against.
That last clause has a name — **differential testing** — and it is
this repository's favourite move: naive against semi-naive, DRed
against Backward/Forward, four evaluation strategies against each
other in the fuzzer, and now two classifiers. A slow, obviously-right
implementation is never wasted work; it is the oracle every fast one
answers to.

## The assumption, recognised

Note what the classifier does *not* say. Nothing in the output claims
`father ⊑ not tall`; unstated simply means unproven. You met this fork
in [Lesson 4](04-closed-and-open-worlds.md): that is the **open-world
assumption**, and this classifier is the reasoner that lesson promised
was living on the other side of it. The observable signature is the
one you saw there — add an axiom here and conclusions only grow, while
adding a fact to a Datalog program can take one away.

## Where this classifier stops

Every other module in this course says where it runs out; here is this
one's boundary, and it matters because the gap to a *real* medical
classifier is exactly one letter of the alphabet.

What ships is **EL⊥**: plain EL plus `disjoint(a, b).` axioms, read
as A ⊓ B ⊑ ⊥. Disjointness buys the one verdict pure EL cannot give —
*this definition is unsatisfiable* — and rules CR5/CR6 above carry the
whole feature: a concept subsumed by ⊥ is reported as unsatisfiable
(and excluded from the hierarchy, where it would otherwise sit under
everything), and an existential with an impossible filler is
impossible. Still missing: **⊤** (no universal concept), **role
hierarchies** (`subrole(has_part, has_component)` is rejected, loudly,
rather than silently ignored), **role chains and right identities**,
nominals, datatypes, and there is no ABox at all: this reasons about
definitions, never about individuals.

SNOMED CT genuinely needs the role hierarchy and right identities
(that's how "a fracture of the femur is a fracture of a bone" and
part-whole propagation work), so it needs **ELH with right identities**
— which is precisely what ELK and Snorocket implement, and precisely
what this file does not. What generalises is the *method*: EL++
reasoners are more completion rules of the same shape, over a richer
normal form. Adding ⊥ was exactly the tractable exercise it looks
like — CR5 and CR6 are what it took; adding role chains is a
research-grade one.

## The tradeoff saga: pick your fragment, and know its price

KL-ONE's own subsumption algorithm was *structural*: normalise both
definitions, compare part by part. Then came the shock results: Brachman
and Levesque (1984) showed that seemingly tiny additions to the concept
language flip subsumption from polynomial to intractable, and
Schmidt-Schauß (1989) proved subsumption in full KL-ONE **undecidable**.
The field's response created **description logics**: pick your fragment
deliberately, and know its price. It is exactly the move Datalog made by
banning function symbols — Lesson 11's boundary, drawn through a
different logic.

There is a twist in that saga worth its own paragraph, because it
decided what SNOMED could be. KL-ONE and its descendants were built
around the **value restriction** (∀, which English renders as "only":
`all(eats, plant)` defines the vegan, someone all of whose food is
plants), with existentials admitted only in
stunted forms; the FL ("frame language") family that the 1984
complexity analysis studied is exactly that shape. For twenty years the
field took "all" to be the indispensable construct and "some" the
dispensable one. The 2000s inverted the bet. Keep only conjunction and
the **existential restriction** — ∃, "some": `some(finding_site,
femur)` says there *is* a site, and it is the femur — and subsumption
stays polynomial even over arbitrarily large, cyclic axiom sets
(Baader 2003; then Baader, Brandt and Lutz's *Pushing the EL
Envelope*, 2005, which stretched the fragment to EL++ without losing
tractability). Keep only value restrictions instead — the logic FL₀ —
and with general axiom sets subsumption is EXPTIME-complete. The
construct the founders treated as the essence turned out to be the
expensive one.

That inversion is why medicine fits. Clinical statements are
existential to the bone — a fracture has *some* site, an infection has
*some* causative agent, a procedure acts on *some* body structure —
and essentially never universal: no definition needs "all findings" of
anything. A terminology that speaks only in "some" lands, by luck of
its subject matter, in exactly the tractable fragment.

## Recognising the fragment in the wild

Nobody hands you an ontology labelled "EL". What you get is a domain
model — an entity–relationship diagram, a class hierarchy, a schema
with subtypes — and the skill this lesson is really for is recognising
that you are looking at a TBox, and *which* TBox. A field guide:

| If your model has... | You are writing... |
|---|---|
| a mandatory link with a fixed target kind | ∃r.C — EL, this lesson's fragment, tractable |
| an optional link ("*if* present, must be...") | ∀r.C — not EL; ask first whether it does any work |
| "defined" kinds vs merely-labelled kinds | ≡ vs ⊑ — and only the defined ones can be *discovered* |
| kinds that must never overlap | `disjoint/2` — EL⊥, which is what ships here |
| helper kinds invented to carry a definition | nested existentials — stop inventing them, the classifier mints its own `gen_N` |
| a ban on cycles so your checker terminates | a symptom: you are doing top-down structural subsumption — bottom-up completion needs no ban (Lesson 6 is the same discovery from the Datalog side) |

The last row deserves its sentence: cyclic definitions are not a
modelling error, they are a *checker* limitation, and the fix is to
change the checker, not the model.

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

## Exercises

1. Add `define(grandmother, and(woman, some(has_child, parent))).` and
   predict the full classification before running it.
2. Add `isa(father, tall).` — why does this *not* make every man tall?
   What would `define(father, ...)` with tall inside do instead?
3. Use `--emit` and `datalog.py --magic` to check a single subsumption
   goal-directedly: `subs(grandfather, parent)`. Which magic facts
   appear?
4. Write an ontology where a concept is discovered *equivalent* to
   another (hint: two syntactically different definitions of the same
   thing: the classifier reports `≡`).

5. A café's menu model, in prose: *an item is a dish or a drink,
   never both; a garnished item is defined as a dish topped with some
   herb; a smoothie is defined as a drink made from some fruit; the
   house special is defined as a dish topped with a garden-grown herb;
   and if an item lists a wine pairing, the pairing must be a wine.*
   Translate what the field guide says is translatable into
   `isa`/`define`/`disjoint` statements, name the one clause that does
   not make it in (and which table row it is), predict the one starred
   discovery before running the classifier, and say which inclusion
   the first `gen_N` name ends up carrying. Then order the confused
   special — a dish that is also a drink — and watch the classifier
   refuse to seat it.

Next: [aggregation](13-aggregation.md) — counting without
contradiction.
