# Lesson 22 — Knowledge graphs: ontologies over data, and values nobody wrote down

Lesson 12 built a classifier that reasons about *definitions*: what a
father is, and therefore what a father must also be. It ended by
admitting what it lacks: "there is no ABox at all: this reasons about
definitions, never about individuals." Most people meet ontologies the
other way round. They have data about individuals (people, companies,
genes, orders) linked into a **knowledge graph**, plus a schema saying
what the links mean, and they want the consequences.

That is Datalog's home ground, and this lesson shows how close: the
W3C's core inference rules for knowledge graphs are a dozen lines of
this course's syntax, and the standards body designed one whole
profile of its ontology language (OWL 2 RL) to be run by a rule
engine. Then it goes one step past Datalog, to rules that **invent
values**, which is the step the ontology people needed and the
database people had already taken. Lessons 4 and 12 are the
prerequisites, and lesson 16 is useful near the end.

## A graph is one relation

**RDF**, the W3C's data model for knowledge graphs, stores everything
as triples: subject, predicate, object. *dana manages sales.
manages is a sub-property of memberOf.* Note the second sentence: in
RDF the schema is stored as triples too, in the same graph as the
data. In Datalog that means one relation:

```prolog
triple(manager, subClassOf, employee).        % schema
triple(employee, subClassOf, person).
triple(memberOf, domain, employee).           % whoever is a member of
triple(memberOf, range, team).                %   something is an employee,
triple(manages, subPropertyOf, memberOf).     %   and what they belong to
triple(manages, domain, manager).             %   is a team
triple(reportsTo, domain, employee).

triple(dana, manages, sales).                 % data
triple(alice, memberOf, sales).
triple(alice, reportsTo, dana).
triple(dana, reportsTo, erin).
```

**RDFS**, the schema vocabulary, has an official list of entailment
rules (numbered rdfs1 to rdfs13 in the RDF Semantics recommendation).
Six of them carry nearly all the weight, and they are ordinary
recursive Datalog over that one relation (`programs/kg.dl`):

```prolog
triple(X, type, C)  :- triple(P, domain, C), triple(X, P, _).          % rdfs2
triple(Y, type, C)  :- triple(P, range, C), triple(_, P, Y).           % rdfs3
triple(P, subPropertyOf, R) :- triple(P, subPropertyOf, Q),
                               triple(Q, subPropertyOf, R).           % rdfs5
triple(X, Q, Y)     :- triple(P, subPropertyOf, Q), triple(X, P, Y).   % rdfs7
triple(X, type, D)  :- triple(C, subClassOf, D), triple(X, type, C).   % rdfs9
triple(C, subClassOf, E) :- triple(C, subClassOf, D),
                            triple(D, subClassOf, E).                 % rdfs11
```

```
$ python3 datalog.py -q 'triple(dana, type, C)' programs/kg.dl
?- triple(dana, type, C)
   triple(dana, type, employee).
   triple(dana, type, manager).
   triple(dana, type, person).
   (3 answers)
$ python3 datalog.py --explain 'triple(dana, type, person)' programs/kg.dl
?- explain triple(dana, type, person)
   triple(dana, type, person)   [via triple(X, type, D) :- triple(C, subClassOf, D), triple(X, type, C).]
     triple(employee, subClassOf, person)   (base fact)
     triple(dana, type, employee)   [via triple(X, type, C) :- triple(P, domain, C), triple(X, P, _).]
       triple(reportsTo, domain, employee)   (base fact)
       triple(dana, reportsTo, erin)   (base fact)
```

Nobody said dana was a person. She reports to someone, only employees
report, and employees are people. Triple stores built on this idea
(RDFox, GraphDB, Jena's rule engine) materialise these consequences
exactly as lesson 2 does, and lesson 10's incremental maintenance is
how RDFox keeps them current as triples arrive.

## The gotcha: `domain` is not a check

The last data triple in the file is a slip. Someone entered a *team*
as reporting to a person:

```prolog
triple(sales, reportsTo, erin).              % a data-entry slip
```

A database person reads `reportsTo` having domain `employee` as a
constraint and expects an error. RDFS has no errors. The domain rule
**infers**: sales reports to someone, so sales is an employee, and so a
person. Nothing complains, because in an open world (lesson 4) the
data is a partial description and anything not contradicted might be
true.

The way to catch it is to state something that *can* be contradicted.
OWL 2 RL (next section) has disjointness, written here as a rule that
derives a `clash` instead of failing:

```prolog
triple(person, disjointWith, team).
clash(X, C, D)  :- triple(C, disjointWith, D),
                   triple(X, type, C), triple(X, type, D).            % cax-dw
```

```
$ python3 datalog.py --explain 'clash(sales, person, team)' programs/kg.dl
?- explain clash(sales, person, team)
   clash(sales, person, team)   [via clash(X, C, D) :- triple(C, disjointWith, D), triple(X, type, C), triple(X, type, D).]
     triple(person, disjointWith, team)   (base fact)
     triple(sales, type, person)   [via triple(X, type, D) :- triple(C, subClassOf, D), triple(X, type, C).]
       triple(employee, subClassOf, person)   (base fact)
       triple(sales, type, employee)   [via triple(X, type, C) :- triple(P, domain, C), triple(X, P, _).]
         triple(reportsTo, domain, employee)   (base fact)
         triple(sales, reportsTo, erin)   (base fact)
     triple(sales, type, team)   [via triple(Y, type, C) :- triple(P, range, C), triple(_, P, Y).]
       triple(memberOf, range, team)   (base fact)
       triple(alice, memberOf, sales)   (base fact)
```

The derivation goes straight to the bad triple, on its seventh line. This is lesson 17's habit at knowledge-graph scale: an
inconsistency is just another derived fact, and its derivation is the
bug report. (The W3C eventually added a separate language for the
closed-world kind of checking, SHACL, in 2017: "every employee
*must have* a manager, and it is an error if none is recorded". The
open world needed a second language to say "missing".)

## OWL 2 RL: the ontology language, cut to fit a rule engine

OWL 2, the W3C ontology language, comes with three **profiles**, each a
fragment chosen for one way of computing:

| Profile | Built for | Lesson |
|---|---|---|
| OWL 2 EL | classifying huge terminologies (SNOMED CT) | 12 |
| OWL 2 QL | rewriting ontology queries into SQL over existing databases | — |
| OWL 2 RL | forward-chaining rules over data | this one |

The RL specification is unusual for a W3C document: its semantics is
given as tables of rules, each with a short name (`eq-sym`,
`prp-trp`, `cax-sco`, and so on). Every rule is Datalog over triples.
`programs/kg.dl` includes three more besides `cax-dw`: transitive
properties and inverses.

```prolog
triple(X, P, Z) :- triple(P, type, transitiveProperty),
                   triple(X, P, Y), triple(Y, P, Z).                  % prp-trp
triple(Y, Q, X) :- triple(P, inverseOf, Q), triple(X, P, Y).           % prp-inv1
```

What RL leaves *out* is the interesting part. In OWL you can say
"every employee works in some department", in description-logic
notation `employee ⊑ ∃worksIn.department`. Lesson 12's EL classifier
handles exactly this axiom, because it reasons about the *concept*
and never needs a particular department. Over data it is different. If
alice is an employee and no department is recorded for her, a reasoner
that took the axiom seriously would have to add a department to the
graph, one that nobody named. OWL 2 RL forbids the existential on the
right-hand side of an axiom for exactly that reason: its rules must
never need to invent anything. That is the boundary between Datalog
and the next section.

## Existential rules: inventing what must exist

Write the axiom as a rule and look at what goes wrong:

```prolog
works_in(E, D) :- employee(E).
```

`D` is bound by nothing. Lesson 1's safety check rejects the rule,
correctly: in Datalog every value in a conclusion must come from the
data, which is what keeps every relation finite. But read the rule as
the ontology means it, "there exists a D", and it is perfectly
sensible. **Existential rules** (tuple-generating dependencies, in
database theory's name) allow exactly this, and the procedure that
evaluates them is **the chase**. Whenever a rule's body matches and
its head is not yet satisfied, invent a fresh value for each
existential variable (a **labelled null**, the self-identical unknown of lesson 19's tour
of nulls, printed here as `_:n1`) and continue.

`chase.py` is this course's chase: ordinary rules are saturated by the
same engine as always, existential rules invent nulls, and the two
alternate until nothing new appears. `programs/org-chart.dl` says
every employee works in some department and every department has
some manager, who is an employee of it. It names only one department
and one manager:

```
$ python3 chase.py -q 'manages(M, D)' -q 'works_in(alice, D)' programs/org-chart.dl
not weakly acyclic: dept[1] =*=> manages[1] -> employee[1] =*=> works_in[2] -> dept[1]
  (a null can feed the rule that invents the next one; termination is not guaranteed)
restricted chase: 3 rounds, 4 labelled nulls invented

?- manages(M, D)
   manages(dana, sales).
   manages(_:n3, _:n1).   [not certain: mentions a null]
   manages(_:n4, _:n2).   [not certain: mentions a null]
   (3 answers, 1 certain)
?- works_in(alice, D)
   works_in(alice, _:n1).   [not certain: mentions a null]
   (1 answer, 0 certain)
```

Ignore the first two lines for a moment. Alice works in `_:n1`, a
department nobody named, and `_:n1` has a manager `_:n3`, also unnamed.
Carol already works in sales and Dana already manages it, so the
**restricted** chase invented nothing for them: a rule fires only if
its conclusion is not already true for *some* value.

Two habits from lesson 4 apply directly:

- **A null is not a NULL.** `_:n1` is one specific unknown department,
  equal to itself and to nothing else. Alice and `_:n3` both work in
  `_:n1`, so they are colleagues. That is a join SQL's NULL would
  refuse (lesson 4, the comparative tour in lesson 19).
- **Certain answers.** "Does alice work somewhere?" is certainly yes.
  "Which department does alice work in?" has no certain answer: every
  model of the rules gives her one, but different models give
  different ones. The engine reports answers mentioning nulls and
  labels them, and answers without nulls are the ones true in every
  model. This is the open world of lesson 4, made computable: absence
  of a recorded department no longer means "none".

## Will it stop?

Inventing values is exactly what safety forbade, so the termination
theorem of lesson 2 is gone. Two programs show the range.

`programs/ancestors-forever.dl` says every person has a parent and
every parent is a person. Each invented parent needs a parent of its
own:

```
$ python3 chase.py --max-nulls 5 programs/ancestors-forever.dl
not weakly acyclic: person[1] =*=> parent[1] -> person[1]
  (a null can feed the rule that invents the next one; termination is not guaranteed)
error: no fixpoint after inventing 5 labelled nulls: the rules are not weakly acyclic -- person[1] =*=> parent[1] -> person[1] -- so the chase may never stop.  (--max-nulls raises the budget.)
```

The first line is a static check that runs before the chase, and it
is lesson 3's idea applied to a new danger. Stratification drew a
graph of predicates and looked for a cycle through negation. **Weak
acyclicity** (Fagin, Kolaitis, Miller and Popa, 2005) draws a graph of
argument *positions* (`person[1]` is the first argument of `person`),
marks with `=*=>` each edge along which a rule invents a null, and
looks for a cycle through a marked edge. No such cycle means the chase
terminates on every database, and that guarantee is the one Datalog
lost and gets back. Here, `person[1] =*=> parent[1] -> person[1]` is
the infinite family tree, named.

The org chart is also not weakly acyclic, yet the restricted chase
finished it in three rounds. The **oblivious** chase, which fires every
rule once per match whether or not the conclusion already holds,
does not:

```
$ python3 chase.py --variant oblivious --max-nulls 20 programs/org-chart.dl
not weakly acyclic: dept[1] =*=> manages[1] -> employee[1] =*=> works_in[2] -> dept[1]
  (a null can feed the rule that invents the next one; termination is not guaranteed)
error: no fixpoint after inventing 20 labelled nulls: the rules are not weakly acyclic -- dept[1] =*=> manages[1] -> employee[1] =*=> works_in[2] -> dept[1] -- so the chase may never stop.  (--max-nulls raises the budget.)
```

The invented manager `_:n3` is an employee, so the oblivious chase
invents a department for them, which needs a manager, who is an
employee, and so on forever. The restricted chase notices that `_:n3`
already works in `_:n1` (they manage it) and stops. Weak acyclicity
is **sufficient, not necessary**, and whether an arbitrary set of
existential rules terminates is undecidable in general (Deutsch, Nash
and Remmel, 2008). The research field built on this is called
**Datalog±** (Calì, Gottlob and Lukasiewicz): Datalog *plus*
existentials, *minus* enough to stay decidable. Its fragments
(guarded, linear, sticky, warded) are where engines like Vadalog,
Nemo and VLog live.

The chase is older than the ontology work, and this course has met
its uses already. Maier, Mendelzon and Sagiv introduced it in 1979 to
decide whether one database dependency implies another, the same Maier
who named Datalog and co-wrote magic sets. It decides **query
containment under constraints**, lesson 16's question once the
database is known to satisfy rules. And it is the procedure lesson 19 said computes CQL's Σ
migration, a left Kan extension, before leaving existential rules as a
signpost. This is the road that signpost pointed down.

## sameAs: the honest hard part

One OWL construct breaks plain Datalog in a different way.
Knowledge graphs are stitched together from several sources, each
with its own name for the same thing, and record linkage connects the
names with `owl:sameAs`. `programs/kg-sameas.dl` has one supplier with
five names (a trading name, a corporate name, a DUNS number, a
purchasing-system id, and so on) and one fact recorded under each.

Equality is expressible as rules, and OWL 2 RL's `eq-*` table does
exactly that: sameAs is reflexive, symmetric and transitive, and any
triple about one name holds for every other name:

```prolog
same(X, X) :- node(X).                                         % eq-ref
same(X, Y) :- sameAs(X, Y).
same(Y, X) :- same(X, Y).                                      % eq-sym
same(X, Z) :- same(X, Y), same(Y, Z).                          % eq-trans
copy(S2, P, O) :- triple(S, P, O), same(S, S2).                % eq-rep-s
copy(S, P, O2) :- copy(S, P, O), same(O, O2).                  % eq-rep-o
```

It is correct, and it is ruinous:

```
$ python3 datalog.py --trace programs/kg-sameas.dl
...
    sizes: copy=30, node=11, same=31
...
    sizes: canon=11, ctriple=6
```

Six stored triples became thirty, and five names produced twenty-five
`same` facts among themselves. With n names for one thing, the
equality relation has n² facts and every triple about the thing is
copied n times. Real linked-data graphs have entities with thousands
of aliases, and materialising equality as rules makes them
unusable.

The cure is not to store equality as a relation at all. Pick one
**representative** per group of equal names, and rewrite every triple
onto representatives:

```prolog
canon(X, min(Y)) :- same(X, Y).
ctriple(CS, P, CO) :- triple(S, P, O), canon(S, CS), canon(O, CO).
```

`ctriple` holds 6 facts, one per real statement, and every query
against it sees one supplier. This version uses lesson 13's `min`
aggregate to choose the representative, and it still computes the n²
`same` relation first, so it shows the *shape* of the fix but not its
efficiency. Real engines replace `same` with a **union-find**
structure: one parent pointer per name, merging two groups in
near-constant time, never materialising the pairs. RDFox handles
sameAs this way, by rewriting with representatives as equalities arrive
(Motik and colleagues, 2015).

There is a second reason the aggregate version is only a sketch. Here
sameAs is input. In full OWL 2 RL, rules *derive* new equalities
(two values of a functional property must be the same thing), and new
equalities change the canonical triples, which can derive further
equalities. The representative choice is then inside the recursion,
which lesson 13 forbade for aggregates. Engines that support this
keep union-find inside the fixpoint loop.

Take that idea one step further, so that when `a = b` the engine also
concludes `f(a) = f(b)` for every term built from them (congruence
closure), and you have **egglog** (Zhang and colleagues, 2023): Datalog
plus a built-in union-find, designed for **equality saturation**, a
technique compilers use to explore every equivalent form of an
expression at once. The language looks like this course's, and its
key data structure is the one this section ended on.

## Where this leaves the two worlds

Lesson 4 ended with an "ontology-plus-rules hybrid". This lesson
filled in the middle of it:

| | Datalog (lessons 1–3) | OWL 2 RL | existential rules (chase) | EL classifier (lesson 12) |
|---|---|---|---|---|
| reasons about | data | data | data | definitions |
| invents values | never | never | yes, labelled nulls | fresh concept names only |
| always terminates | yes | yes | no; weak acyclicity is a check | yes |
| absence means | false | unknown, but RL rules never ask | unknown, with certain answers | unknown |

Knowledge graphs are also where language models now meet this
material: extracting triples from documents is cheap, and a graph full
of extracted triples needs exactly the checks above. A disjointness
clash with a derivation is a far better review queue than a reviewer
reading every triple.

## Exercises

1. Add `triple(reportsTo, range, employee).` to `programs/kg.dl` and
   predict which new `type` triples appear, including erin's. Does
   any new clash appear?
2. Fix the data-entry slip in two different ways (change the triple,
   or change the schema), and say which one a curator should prefer
   and why the clash rule cannot decide that for you.
3. In `programs/org-chart.dl`, change `works_in(M, D) :- manages(M, D).`
   to say managers work in *some* department, not the one they manage.
   Does the restricted chase still stop? Explain using the trace of
   which trigger is no longer satisfied.
4. Write a weakly acyclic version of "every person has a parent" that
   still says something useful. (Hint: stop the recursion by giving
   invented people a different predicate.) Check it with `chase.py`.
5. Add a sixth name for the supplier to `programs/kg-sameas.dl`.
   Predict `same`, `copy` and `ctriple` sizes before running it. Then
   add a second, unrelated supplier with two names, and check that the
   two suppliers are never merged.
6. Lesson 16's containment test treats a query body as a database.
   Given the rule `works_in(E, D) :- employee(E).`, is
   `q(E) :- employee(E), works_in(E, D).` equivalent to
   `q(E) :- employee(E).` on every database that satisfies the rule?
   Run the chase on the first query's frozen body to decide.

Back to [the index](getting-started.md), or to lesson 0's list of
[places Datalog earns its living](00-what-is-datalog.md#five-places-datalog-earns-its-living),
which this lesson and the two before it have now visited in code.
