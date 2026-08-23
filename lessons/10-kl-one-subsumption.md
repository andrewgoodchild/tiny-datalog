# Lesson 10 — KL-ONE and subsumption: reasoning about definitions

Everything so far reasoned about *facts*: which tuples are in which
relations. This lesson's question is one level up: what follows from
**definitions themselves**? If a Father is "a man with a child", and a
Parent is "a person with a child", then every father is a parent — no
data required. That inference is called **subsumption**, and the system
that made it famous is KL-ONE.

## KL-ONE and the classifier

KL-ONE (Ron Brachman, late 1970s) reorganised the era's loose "semantic
networks" and frames into something with actual semantics: **concepts**
with structured definitions built from other concepts and **roles**
(relations). Its celebrated feature was the *classifier* — assert a new
concept's definition and the system computes, automatically, where it
belongs in the hierarchy. The reasoning service underneath:

> C is **subsumed** by D (written C ⊑ D) iff every possible instance of
> C must be an instance of D, in every world consistent with the
> definitions.

Note what changed from the last nine lessons: this is *terminological*
reasoning (a "TBox," about concepts), not *assertional* reasoning (an
"ABox," about individuals). Datalog answers "which tuples?"; subsumption
answers "which definitions entail which?"

## The tradeoff saga — the same lesson as Lesson 9, rediscovered

KL-ONE's own subsumption algorithm was *structural*: normalise both
definitions, compare part by part. Then came the shock results: Brachman
and Levesque (1984) showed that seemingly tiny additions to the concept
language flip subsumption from polynomial to intractable, and
Schmidt-Schauß (1989) proved subsumption in full KL-ONE **undecidable**.
The field's response created **description logics**: pick your fragment
deliberately, and know its price. It is exactly the move Datalog made by
banning function symbols — Lesson 9's boundary, drawn through a
different logic.

The fragment this lesson implements is **EL**: conjunction (`and`) and
existential restriction (`some`), nothing else. Subsumption in EL is
polynomial — and EL is no toy: it is the tractable core underneath the
OWL 2 EL profile, the family that reasoners like ELK and Snorocket
scale to SNOMED CT, the ~350,000-concept clinical terminology used in
health records worldwide.

## The punchline: subsumption compiles to Datalog

EL subsumption is decided by a *saturation calculus*: normalise the
ontology into four axiom shapes, then apply completion rules to fixpoint.
Monotone rules, run to fixpoint — that is a Datalog program. So this
repository's implementation (`subsumption.py`) is a **compiler**: it
normalises the ontology, emits facts plus five rules, and hands them to
the engine you already know. Try `--emit` to see the generated program;
it runs under plain `datalog.py`.

The ontology (`programs/10-family-ontology.dl` — note it uses the
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
$ python3 subsumption.py programs/10-family-ontology.dl
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
is a parent — and every grandfather is a *father* (having a child who is
a parent is, in particular, having a child who is a person). That
asterisked discovery is KL-ONE's party trick, reproduced by six Datalog
rules.

Two details worth reading in `subsumption.py`: normalisation mints fresh
names (`gen_1`, ...) for nested expressions, choosing the inclusion's
direction by which side of ⊑ the expression sits on — a conservative
extension, and essentially the structural normalisation KL-ONE performed;
and the five completion rules in `datalog()` are the CR1–CR4 calculus
that industrial EL reasoners (ELK, Snorocket) implement with exactly the
optimisations this course already taught: saturation is semi-naive
fixpoint, and goal-directed subsumption checks are magic sets.


## Where this classifier stops

Every other module in this course says where it runs out; here is this
one's boundary, and it matters because the gap to a *real* medical
classifier is exactly one letter of the alphabet.

What ships is plain **EL**. Missing: **⊤** (no universal concept), **⊥
and disjointness** (so this classifier can never tell you a definition
is unsatisfiable — a significant thing for a knowledge base to be
unable to say), **role hierarchies** (`subrole(has_part, has_component)`
is rejected, loudly, rather than silently ignored), **role chains and
right identities**, nominals, datatypes — and there is no ABox at all:
this reasons about definitions, never about individuals.

SNOMED CT genuinely needs the role hierarchy and right identities
(that's how "a fracture of the femur is a fracture of a bone" and
part-whole propagation work), so it needs **ELH with right identities**
— which is precisely what ELK and Snorocket implement, and precisely
what this file does not. What generalises is the *method*: EL++
reasoners are more completion rules of the same shape, over a richer
normal form. Adding ⊥ alone is a genuinely tractable exercise; adding
role chains is a research-grade one.

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
   thing — the classifier reports `≡`).

Next: [under the hood](11-under-the-hood.md) — how all of it is built.
