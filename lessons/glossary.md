# Glossary

Every technical term the course uses, with the lesson that introduces
it. Alphabetical, so you can arrive here from anywhere.

---

**ABox.** The assertional part of a knowledge base: statements about
*individuals* ("bob is a Father"). Contrast **TBox**. `subsumption.py`
has no ABox at all; it reasons only about definitions. *(Lesson 12)*

**Absorption.** The semiring law `A + A·B = A`: a witness set that
contains another is discarded as redundant. It is what makes
why-provenance a *quotient* of the provenance polynomial, and therefore
lossy. *(Lesson 8)*

**Adornment.** A string of `b`/`f` marking which arguments of a
predicate are bound (known) or free at call time. `path#bf` is "path,
called with the first argument known". The bookkeeping magic sets runs
on. *(Lesson 7)*

**Aggregation.** Collapsing many body solutions into one value:
`sum`, `count`, `min`, `max`. Written in the rule head,
`total(P, sum(A)) :- charge(P, C, A).`, where the remaining head
arguments are the implicit GROUP BY. *(Lesson 13)*

**AGM bound.** The tight limit (Atserias–Grohe–Marx) on how large a
conjunctive query's output can be given its relation sizes. Pairwise
join plans can exceed it asymptotically on intermediate results;
**worst-case optimal joins** cannot. *(Lesson 7)*

**Alternating fixpoint.** Van Gelder's method for computing the
well-founded model: iterate the (antimonotone) Gelfond–Lifschitz
operator twice, which is monotone, and read the undefined atoms off the
gap between the result and its image. *(Lesson 5)*

**Ambiguity blocking / propagating.** Two readings of an unresolved
conflict in defeasible logic. *Blocking* (the default) lets an attacker
count only once its body is proved, so the doubt stays where it arose.
*Propagating* lets a merely supported attacker count, so the doubt
spreads to whatever depends on it. *(Lesson 18)*

**Answer Set Programming (ASP).** The branch of logic programming
where a program is written so that its **stable models** *are* the
solutions to a combinatorial problem. `clingo` is the standard
implementation. *(Lessons 0, 5)*

**Arity.** The number of arguments a predicate takes. `path/2` means
`path` with arity 2. This engine requires arity to be consistent across
a program. *(Lesson 1)*

**Atom.** A predicate applied to terms: `parent(abe, bob)` or
`path(X, Y)`. A **ground** atom has no variables. *(Lesson 1)*

**Attenuation.** Restricting a capability token without contacting
its issuer, by appending checks. In Biscuit a token is authorized only
if every check passes, so appending a block adds a conjunct and can
only shrink what the token permits. *(Lesson 20)*

**Backward/Forward (B/F).** The 2015 deletion algorithm (Motik, Nenov,
Piro, Horrocks; implemented in RDFox): compute the facts affected by a
deletion, then confirm each by backward chaining for an alternative,
well-founded derivation before removing anything. The check-first
counterpart to **DRed**'s demolish-first. *(Lesson 10)*

**Base fact.** See **EDB**.

**BFS (breadth-first search).** Explore a graph level by level. Used
here only to reconstruct the shortest offending cycle when
stratification fails. *(Lesson 3)*

**Bitemporal.** Data that records two times for each fact: when it was
true (**valid time**) and when it was recorded (**transaction time**).
It answers "as known on K, what held on T?", which an audit needs and
a table of current state cannot give. *(Lesson 23)*

**Body.** The part of a rule to the right of `:-`, a conjunction of
literals. The **head** is to the left. *(Lesson 1)*

**Bottom-up evaluation.** Start from the facts and apply rules
forwards until nothing new appears. What `datalog.py` does. Contrast
**top-down**. *(Lesson 2)*

**Built-in.** An operation like `X != Y` or `Z = X + 1` evaluated by
the engine rather than looked up in a relation. Safe only under a
**mode** discipline saying which arguments must be ground — and safe
for termination only if it filters the Herbrand universe rather than
growing it, which is why `!=` is harmless and unbounded `+` is not.
*(Lesson 14)*

**Call graph.** Which methods each call site may invoke. With virtual
dispatch it depends on **points-to** information, which depends on the
call graph in turn, so precise analyses compute both in one fixpoint.
*(Lesson 21)*

**CALM theorem.** Consistency As Logical Monotonicity: a distributed
program can be run without coordination exactly when it is monotone,
which for Datalog means negation-free. *(Lesson 0)*

**Canonical instance.** A query's own body, with its variables frozen
into fresh constants: the smallest, most hostile database satisfying
the query. Testing against it stands in for testing against all
databases (Chandra–Merlin). *(Lesson 16)*

**Capability.** A token that carries its own permissions, so the
service receiving it can decide without a central policy store.
Biscuit's capabilities contain Datalog. *(Lesson 20)*

**Certain answer.** An answer true in every model of the data and
rules. Over a chase result, answers mentioning a **labelled null** are
not certain: "alice works somewhere" is certain, "alice works in
`_:n1`" names no particular department. *(Lesson 22)*

**Chandra–Merlin theorem.** For conjunctive queries, Q2 contains Q1
iff there is a **homomorphism** from Q2's body into Q1's body fixing
the head variables. Turns a question about infinitely many databases
into a finite search. *(Lesson 16)*

**Chase.** The procedure that evaluates **existential rules**: when a
rule's body matches and its head is not yet satisfied, invent a
**labelled null** for each existential variable and continue.
Introduced by Maier, Mendelzon and Sagiv (1979) for reasoning about
dependencies; `chase.py` implements the restricted and oblivious
variants. *(Lesson 22)*

**Class hierarchy analysis (CHA).** Resolving a virtual call by
method name alone, with no **points-to** information. Cheap, and it
reports every method of that name as a possible target. *(Lesson 21)*

**Classification.** Computing the full subsumption hierarchy of an
ontology, i.e. discovering where every concept belongs. KL-ONE's
signature feature. *(Lesson 12)*

**Closed-world assumption (CWA).** Absence means false: if a fact
cannot be derived, it is taken to be untrue. What makes negation
computable, and what makes missing data dangerous. Contrast **OWA**.
*(Lessons 3, 4)*

**Coalescing.** Merging overlapping or adjacent intervals that carry the
same value into one interval, so that counting or summing over
intervals does not count one period twice. *(Lesson 23)*

**Coinduction.** Truth by unfalsifiability: a fact holds because no
finite refutation of it exists, where induction demands a finite proof.
The natural reading of properties over cyclic structures — subtyping
of recursive types, bisimulation — and computable in stratified
Datalog by deriving the refutation inductively and negating it.
*(Lesson 6)*

**Combined complexity.** Cost when both the rules and the data are
allowed to vary. Datalog is EXPTIME-complete here, and the exponential
lives in the number of variables per rule. Contrast **data
complexity**. *(Lesson 2)*

**Comparison.** A built-in literal `X < Y` (also `<=`, `>`, `>=`, `=`,
`!=`) that checks two values and produces none. Both sides must be
bound, so a comparison can only filter, which is why it is safe when
`+` is not. Numbers compare as numbers, strings as text. *(Lessons 14,
23)*

**Completion rules.** The saturation calculus that decides EL
subsumption (CR1–CR4 plus reflexivity). Monotone rules run to fixpoint,
which is why they compile to Datalog. *(Lesson 12)*

**Compound term.** A term with structure, like `s(N)` or
`cons(H, T)`. Also called a **function symbol** application. Datalog
bans them; `prolog.py` allows them. *(Lesson 11)*

**Conjunctive query.** A single rule with no negation and no
recursion: the SELECT–FROM–WHERE of Datalog. The fragment where
containment is decidable. *(Lesson 16)*

**Constant.** A value: `bob`, `42`, `"Mary Jane"`. Lowercase
identifiers, numbers, or quoted strings. *(Lesson 1)*

**Containment.** Q2 ⊇ Q1 means every answer to Q1 is an answer to Q2
*on every database*. **Equivalence** is containment both ways.
*(Lesson 16)*

**Context sensitivity.** Distinguishing a method's variables by the
calling context (call sites, or receiver objects), so that values
passed in at one call do not come out at another. It trades fact count
for precision. *(Lesson 21)*

**Counterexample.** A way of matching an **integrity constraint**'s
body: a set of facts showing the property fails. Printed as the body
made ground, so each fact in it can be explained. *(Lesson 17)*

**DAG (directed acyclic graph).** A directed graph with no cycles.
Transitive closure over one always terminates quickly; the interesting
cases in this course are the graphs that are *not* acyclic. *(Lesson 8)*

**Data complexity.** Cost when the program is held fixed and only the
data grows, which is the realistic case: small rule sets, enormous
tables. Datalog is PTIME-complete here. The gap between this and
**combined complexity** is why "Datalog is polynomial" and "Datalog is
exponential" are both true. *(Lesson 2)*

**Datalog.** A query language of function-free Horn clauses evaluated
bottom-up. Declarative, recursive, and guaranteed to terminate.
*(Lesson 0)*

**Datalog°.** Current research defining program semantics as a least
fixpoint in an *ordered semiring*, characterising when convergence and
semi-naive evaluation still hold. *(Lesson 8)*

**Datalog±.** Datalog *plus* existential rules, *minus* enough
(guarded, linear, sticky, warded fragments) that query answering stays
decidable. Vadalog, Nemo and VLog implement members of the family.
*(Lesson 22)*

**DBSP.** The algebraic foundation for incremental computation (VLDB
2023): programs become circuits over **Z-sets**, every operator gets a
uniform derivative, and insertion and deletion stop being different
algorithms. Generalises semi-naive evaluation to arbitrary changes; the
Feldera engine implements it, programmed in SQL. *(Lesson 10)*

**Decidable.** A question a terminating procedure can always answer.
Datalog is built out of deliberate restrictions that keep questions
decidable: termination, stratifiability, and containment for
non-recursive queries are all decidable, and each becomes
**undecidable** just outside the fence. *(Lessons 3, 11, 16)*

**Default reasoning.** "P holds unless something says otherwise", the
Tweety pattern: `flies(X) :- bird(X), not abnormal(X).` Requires CWA
and is therefore **non-monotone**. **Defeasible logic** makes it
first-class. *(Lessons 3, 4, 18)*

**Defeasible logic.** Nute's logic of rules with exceptions: strict
rules (`->`), defeasible rules (`=>`) that hold unless defeated,
**defeaters** (`~>`), and a **superiority relation** saying which rule
wins a conflict. Conclusions carry **proof tags**. *(Lesson 18)*

**Defeater.** A rule that can only attack. `injured(X) ~> ~flies(X)`
blocks `flies` without proving `~flies`. *(Lesson 18)*

**Delta.** The set of facts newly derived in the previous round. The
central object of semi-naive evaluation and of incremental
maintenance. *(Lessons 2, 10)*

**Dependency graph.** Predicates as nodes, "uses in a rule body" as
edges, labelled positive, negative, or aggregating. Stratification is a
question about its cycles. *(Lesson 3)*

**DRed (delete and rederive).** The 1993 algorithm for deleting from a
materialised view: over-delete everything reachable from the removed
fact, then re-derive whatever still has support. Contrast
**Backward/Forward**, which checks before deleting. *(Lesson 10)*

**EDB (extensional database).** The predicates defined by facts, i.e.
your input data. Contrast **IDB**. *(Lesson 1)*

**EL.** The description logic of conjunction and existential
restriction, with polynomial-time subsumption. The tractable core
underneath OWL 2 EL (this repository ships **EL⊥**, adding
disjointness). **EL++** and **ELH** add role hierarchies and
right identities. *(Lesson 12)*

**Episode.** In lesson 24, one conversation the memory learned from. Each
stated fact carries its episode id, so every derivation ends at the
conversations that caused it. *(Lesson 24)*

**Equivalence.** See **Containment**.

**Existential rule.** A rule with a head variable no body literal
binds, read as "there exists": `works_in(E, D) :- employee(E).`
Plain Datalog's safety check forbids it, and the **chase** evaluates
it. Also called a tuple-generating dependency (TGD). *(Lesson 22)*

**Extraction boundary.** The line between a language model and a rule
engine in a memory system: the model turns text into stated facts, and
everything after that is rules. Nothing the rules derive is written by
the model. *(Lesson 24)*

**F-logic.** Frame Logic (Kifer–Lausen 1989): objects, attributes and
class hierarchies as first-class logical syntax, whose rule fragment
compiles to Datalog over a fixed vocabulary (`attr`/`isa`/`sub` plus
bridge rules). The closed-world counterpart to description logics in
the ontology wars; its encoding survives as entity–attribute–value.
*(Lesson 19)*

**Fact.** A rule with an empty body; a ground atom asserted outright.
*(Lesson 1)*

**Fail open / fail closed.** What an access rule does when the data
it depends on is missing. `not suspended(U)` over an empty list grants
everyone access (fails open); requiring a fact that the list was
loaded refuses everyone (fails closed). *(Lesson 20)*

**Fixpoint.** A set unchanged by applying the rules again; the point
at which evaluation stops. The **least fixpoint** is the smallest such
set, and is what a Datalog program means. *(Lesson 2)*

**Free object.** An algebraic structure satisfying only the equations
it must: any assignment of its generators into another structure of
the same kind extends to exactly one homomorphism. The provenance
polynomials ℕ[X] are the free commutative semiring, which is why every
semiring's answer factors through them. *(Lesson 8)*

**Function symbol.** See **Compound term**.

**Functional relation.** A relation with one value at a time per
subject, such as an employer. A later statement about it supersedes
an earlier one; statements about a non-functional relation, such as
who someone knows, accumulate. *(Lesson 23)*

**Functor.** A structure-preserving map between categories. In CQL a
database instance *is* a functor from the schema to sets, so violating
a constraint means failing to be an instance at all. *(Lesson 19)*

**Gelfond–Lifschitz reduct.** Given a candidate model S, delete every
rule whose negated atoms are in S and strip the remaining negations.
What is left is negation-free; M is a **stable model** iff the reduct's
least model is exactly M. *(Lesson 5)*

**Greatest fixpoint.** The largest set a monotone operator maps to
itself, dual to the least fixpoint of Lesson 2. Obtainable in
stratified Datalog as the complement of the least fixpoint of the
complemented operator — which is exactly Lesson 6's construction.
*(Lessons 6, 18)*

**Ground.** Containing no variables. A ground atom is a specific fact;
**grounding** a program means instantiating its rules over all
constants. *(Lessons 1, 5)*

**Head.** The atom to the left of `:-`, the conclusion a rule draws.
*(Lesson 1)*

**Herbrand universe / base.** The set of all constants in a program,
and all ground atoms buildable from them. Finite for Datalog, infinite
once function symbols appear, which is exactly why Datalog
terminates. *(Lesson 11)*

**Homomorphism.** A map from one structure's variables to another's
terms that sends every atom onto an atom. Finding one is what `match`
(in `core.py`) does against a database, and what containment does against another
query body. *(Lesson 16)*

**Horn clause.** A formula with at most one positive literal, i.e.
exactly the shape `head :- body`. Datalog is Horn clauses without
function symbols. *(Lesson 11)*

**IDB (intensional database).** The predicates defined by rules, i.e.
what the program derives. Contrast **EDB**. *(Lesson 1)*

**Idempotent.** An operation where `a + a = a`. Idempotent semirings
(min-plus, boolean) converge on cyclic programs where counting
diverges. *(Lesson 8)*

**Immediate consequence operator (T_P).** The function taking a set of
facts to everything derivable from it in one step. Evaluation is
iterating it to a fixpoint. *(Lesson 2)*

**Incremental view maintenance.** Updating derived relations after the
input changes, rather than recomputing. Insertions resume semi-naive;
deletions need **DRed**. *(Lesson 10)*

**Integrity constraint.** A rule with no head, `:- body.`, whose body
must never hold. It derives nothing; after evaluation, every match is
reported as a **counterexample**, and the CLI exits with status 3. A
check on the data in hand, not a proof for all data. *(Lesson 17)*

**Join.** Combining two relations on shared variables. In this engine
a rule body *is* a join, performed by folding `match` over its
literals under one growing substitution. *(Lesson 1)*

**Kan extension.** Category theory's universal way of extending a
functor along another; CQL's data-migration operators Σ and Π are the
left and right Kan extensions, and the chase computes the left one.
*(Lesson 19)*

**Knaster–Tarski theorem.** A monotone function on a complete lattice
has a least fixpoint. Applied to the immediate consequence operator on
the (finite) powerset lattice of facts, it is the two-line reason every
Datalog program terminates with a unique meaning. *(Lesson 2)*

**Knowledge graph.** Data stored as subject–predicate–object
**triples**, usually with a schema stored as triples too. RDF is the
W3C's data model for them. *(Lesson 22)*

**Kunen semantics.** A three-valued semantics of logic programs with
negation, built from finite proofs of truth and of failure. Unlike the
**well-founded semantics** it does not refute unfounded loops. Standard
defeasible logic is exactly Kunen's semantics of a program that encodes
the theory (Maher & Governatori 1999). *(Lesson 18)*

**Labelled null.** Database theory's honest unknown: an invented
witness ("someone, unspecified") that is *self-identical* across
occurrences, unlike SQL's NULL. Produced by the **chase** for
existential rules, and printed by `chase.py` as `_:n1` (RDF calls the
same thing a blank node). `subsumption.py`'s `gen_N` names are
miniature ones. *(Lessons 4, 19, 22)*

**Lattice.** A partially ordered set where any two elements have a
meet and a join; here, all possible fact-sets ordered by ⊆. The stage
on which Knaster–Tarski performs. *(Lesson 2)*

**Literal.** An atom, a negated atom (`not p(X)`), or a **comparison**
(`X < Y`). *(Lessons 3, 23)*

**Magic sets.** A program rewriting that makes bottom-up evaluation
goal-directed, by adding **magic predicates** recording which bindings
are actually demanded. *(Lesson 7)*

**Materialisation.** The stored result of evaluating a program; what
incremental maintenance keeps up to date. *(Lesson 10)*

**Minimisation.** Finding the smallest rule body equivalent to the one
you wrote, by dropping atoms a homomorphism can repair. *(Lesson 16)*

**Model.** A set of facts satisfying every rule. The **least model**
is the smallest one, and is the meaning of a positive program.
*(Lessons 2, 5)*

**Monotone / non-monotone.** Monotone means adding facts can only add
conclusions. Positive Datalog is monotone; negation and aggregation are
not, which is why both need stratification. *(Lessons 3, 13, 4)*

**Naive evaluation.** Applying every rule to the whole database every
round, rediscovering everything each time. The baseline semi-naive
improves on; `--naive` runs it. *(Lesson 2)*

**Negation as failure.** `not p` succeeds when `p` cannot be derived.
Not classical negation: it is a statement about the database, not the
world. *(Lesson 3)*

**Null.** Not one concept: SQL's single marker covers *unknown*,
*inapplicable* and *withheld* (with a three-valued logic as the bill);
programming's null reference is absence-as-crash; Datalog has none —
optional data decomposes into optional relations, and absence itself
carries the meaning (see **CWA**/**OWA**). *(Lesson 4)*

**Occurs check.** Refusing to unify `X` with a term containing `X`,
which would build an infinite term. `prolog.py` performs it; real
Prolog usually skips it for speed. *(Lesson 11)*

**Open-world assumption (OWA).** Absence means unknown: unstated facts
are neither true nor false. Description logics assume it; consequently
they are **monotone** and cannot express defaults. *(Lesson 4)*

**OWL 2 RL.** The profile of the W3C ontology language designed to be
evaluated by forward-chaining rules over data. Its semantics is
published as tables of rules (`eq-sym`, `prp-trp`, `cax-sco`, ...), and
it excludes the existential axioms that would need the **chase**.
*(Lesson 22)*

**Points-to analysis.** Computing, for each variable, the set of heap
objects (named by allocation site) it may refer to. The flagship
Datalog program analysis: Doop, bddbddb and CodeQL are built on it.
*(Lessons 2, 21)*

**Predicate.** The name of a relation: `parent`, `path`, `eligible`.
*(Lesson 1)*

**Primitive vs defined concept.** `isa` states a *necessary*
condition; `define` states necessary **and sufficient** ones. Only
defined concepts can be *discovered* to sit beneath something nobody
stated. *(Lesson 12)*

**Proof tag.** In defeasible logic, +Δ q (definitely q), −Δ q
(demonstrably not definitely), +∂ q (defeasibly q), −∂ q (demonstrably
not defeasibly). A literal with neither +∂ nor −∂ is *undecided*.
*(Lesson 18)*

**Provenance.** The record of *why* a fact holds. **Why-provenance**
gives minimal sets of base facts (**witnesses**); **provenance
polynomials** (ℕ[X]) additionally keep multiplicity and are the free
semiring, so everything else factors through them. *(Lesson 8)*

**PTIME-complete.** As hard as any problem solvable in polynomial
time, so (barring a complexity-theoretic surprise) inherently
sequential: not parallelisable to polylogarithmic time. Datalog's data
complexity is PTIME-complete, which is a statement about its power as
well as its cost. *(Lesson 2)*

**QSQR.** Query-Subquery Recursive, the set-at-a-time top-down
evaluation strategy `tabling.py` implements. *(Lesson 15)*

**Range restriction.** See **Safety**.

**RDFS.** RDF Schema: the vocabulary (`subClassOf`, `subPropertyOf`,
`domain`, `range`) for describing a **knowledge graph**, with
entailment rules that are plain recursive Datalog. `domain` and
`range` *infer* types; they never reject data. *(Lesson 22)*

**ReBAC.** Relationship-based access control: access is a path in a
graph of users, groups and objects, as in Google's Zanzibar, rather
than a lookup in a role table. *(Lesson 20)*

**Recursion.** A predicate defined in terms of itself.
**Linear** recursion has one recursive body literal; **non-linear** has
several, which reaches the fixpoint in logarithmically many rounds.
**Left recursion** puts the recursive call first, which defeats SLD but
not tabling. *(Lessons 2, 15)*

**Restricted / oblivious chase.** Two variants of the **chase**. The
restricted chase fires a rule only if its head is not already
satisfied by some existing fact, and the oblivious chase fires every
match once. The restricted chase invents fewer nulls and terminates
more often. *(Lesson 22)*

**Role.** A binary relation in a description logic (`has_child`).
A **role hierarchy** relates roles to each other; not supported here.
*(Lesson 12)*

**Safety (range restriction).** Every variable in a rule head, under
`not`, or in a comparison must also appear in a positive body literal.
What keeps every derived relation finite. *(Lessons 1, 3, 23)*

**sameAs.** OWL's equality between names (`owl:sameAs`). As rules it
needs reflexivity, symmetry, transitivity and replacement, which copies
every fact onto every alias (n² equality facts for n names). Engines
rewrite onto one representative per class, kept in a **union-find**.
*(Lesson 22)*

**Semi-naive evaluation.** Re-joining rules only against the previous
round's **delta** rather than the whole database. The standard
bottom-up optimisation, and the ancestor of incremental view
maintenance. *(Lesson 2)*

**Semiring.** A set with `+` and `×`, each with an identity. Attach a
semiring value to every fact, multiply along a derivation and add
across derivations, and the same program computes reachability, cost,
counts, provenance, or probability. *(Lesson 8)*

**Sentinel.** A value that stands for something outside the domain,
such as `"9999-12-31"` for an interval with no end yet. A convention,
not logic, and shared with SQL's temporal tables. *(Lesson 23)*

**Sideways information passing (SIPS).** The order in which bindings
flow through a rule body, determining the adornments magic sets
generates. Here it is simply left to right, matching the evaluator.
*(Lesson 7)*

**SLD resolution.** The top-down proof procedure of Prolog: unify the
goal with a rule head, then prove the body. Tuple-at-a-time, and
vulnerable to left recursion. **SLG** adds tabling. *(Lessons 11, 15)*

**SLG resolution.** Tabling for programs with negation through
recursion (Chen & Warren 1996; XSB Prolog). It suspends and resumes
calls instead of re-running them, detects when a group of tables is
complete, and *delays* negative literals it cannot yet decide.
Answers whose delays never resolve come out *undefined*: the
**well-founded semantics**, computed top-down. *(Lesson 15)*

**Source / sink / sanitizer.** The vocabulary of **taint analysis**: a
source introduces untrusted data, a sink must not receive it, and a
sanitizer's output is treated as clean. *(Lesson 21)*

**Stable model.** A set of facts that justifies itself: the
Gelfond–Lifschitz reduct with respect to it derives exactly it. A
program may have one (determinate), none (contradictory), or several
(underspecified). *(Lesson 5)*

**Stratification.** Partitioning predicates into **strata** so that
nothing depends on its own negation (or aggregation), then evaluating
stratum by stratum. Syntactic, decidable, and the condition this engine
enforces. *(Lessons 3, 13)*

**Strong negation.** `~p` as a claim of its own, not the absence of
`p`. In defeasible logic a conflict is exactly a pair `p`, `~p`.
Contrast **negation as failure**. *(Lesson 18)*

**Strongly connected component (SCC).** A maximal set of mutually
reachable nodes in the dependency graph. Every cycle lives inside one,
so stratifiability reduces to "no strict edge inside an SCC".
*(Lesson 3)*

**Substitution.** A mapping from variables to values, built up while
matching a rule body. *(Lesson 1)*

**Subsumption.** C ⊑ D: every possible instance of C must be an
instance of D, in every world consistent with the definitions. A
statement about definitions, not data. *(Lesson 12)*

**Superiority relation.** An acyclic order on rules, written `r1 > r2`:
when r1 and r2 support complementary conclusions, r1 wins. Defeasible
logic infers no priorities; every one is stated. *(Lesson 18)*

**Supersession.** One statement ending another: a later statement about
a **functional relation** bounds the validity of the earlier one, which
stays on record. Non-monotone, since a new fact retracts a conclusion.
*(Lesson 23)*

**Tabling.** Top-down evaluation that memoises each subgoal's answers
in a **table**, so recursive calls read the table instead of
descending. Gives Prolog-style goal direction with Datalog-style
termination. *(Lesson 15)*

**Taint analysis.** Tracking whether data from a **source** can reach
a **sink**: reachability over value-flow edges. A finding's derivation
is the path through the code. *(Lesson 21)*

**TBox.** The terminological part of a knowledge base: the definitions
themselves. Contrast **ABox**. *(Lesson 12)*

**Team defeat.** In defeasible logic, the rules for q win as a team:
each attacker of q must be beaten by *some* applicable rule for q, not
necessarily the one that supports q. *(Lesson 18)*

**Term.** A constant, a variable, or (outside Datalog) a compound
term. *(Lesson 1)*

**Top-down evaluation.** Start from the query and work backwards to
the facts. Natively goal-directed; see **SLD resolution** and
**tabling**. *(Lessons 11, 15)*

**Transaction time.** When a fact was recorded, as opposed to when it
was true (**valid time**). See **Bitemporal**. *(Lesson 23)*

**Triple.** One subject–predicate–object statement of a **knowledge
graph**. In Datalog, a graph is the single relation
`triple(S, P, O)`. *(Lesson 22)*

**Undecidable.** No terminating procedure can answer it in general.
Whether an arbitrary Horn-clause program halts (Lesson 11), and whether
one *recursive* Datalog program contains another (Shmueli 1993, Lesson
16), are both undecidable, which is precisely why this engine bans
function symbols and `containment.py` refuses recursion. *(Lessons 11, 16)*

**Unification.** Making two terms equal by binding variables, where
*both* sides may contain variables. Matching against a ground database
is the one-way special case. *(Lesson 11)*

**Union-find.** A data structure that maintains equivalence classes
under merging, in near-constant time per operation, with one parent
pointer per element. Engines use it to handle **sameAs** without
materialising the n² pairs; egglog makes it a first-class part of
Datalog. *(Lesson 22)*

**Valid time.** When a fact was true in the world, usually a half-open
interval `[From, Until)`. See **Bitemporal**. *(Lesson 23)*

**Variable.** A placeholder, written with an initial capital or
underscore: `X`, `Cook`, `_`. *(Lesson 1)*

**Viterbi semiring.** (max, ×) over [0,1]: the probability of the most
likely single derivation. A genuine semiring, unlike "total
probability", which is not. *(Lesson 9)*

**Warning (lint).** A message, on stderr, about a program that is legal
but probably wrong: a predicate nothing defines (usually a typo, so the
nearest name is suggested), a predicate with no base case, or
comparisons that contradict each other. *(Lessons 17, 23)*

**Weak acyclicity.** A static test that guarantees the **chase**
terminates (Fagin, Kolaitis, Miller and Popa, 2005): draw a graph of
argument positions, mark the edges along which rules invent nulls, and
check that no cycle passes through a marked edge. Sufficient, not
necessary. *(Lesson 22)*

**Well-founded semantics.** A three-valued semantics (true, false,
**undefined**) that always exists, settling what it can and naming what
is genuinely circular. *(Lesson 5)*

**What-if (`--assume`).** Evaluating as though some facts were added
(`edge(a, z).`) or removed (`edge(a, b)~.`), without editing the
program. Constraints are checked against the hypothetical database, so
a batch can be tried before it is stored. *(Lesson 24)*

**Witness.** A minimal set of base facts sufficient to derive a
conclusion; why-provenance returns the set of them. *(Lesson 8)*

**Worst-case optimal join.** A join algorithm (leapfrog triejoin is
the widely implemented one) whose running time is bounded by the AGM
bound — the largest the *answer* could be — rather than by the size of
any intermediate. The cure for the half of the performance story magic
sets does not touch. *(Lesson 7)*

**Z-set.** A collection where each fact carries a signed integer
multiplicity: +1 is an insertion, −1 a deletion, and a change is data
flowing through the same operators as the facts themselves. The
representation underneath **DBSP**, and what plain sets cannot express
("this fact lost one of its two supports"). *(Lesson 10)*

**Zanzibar.** Google's global authorization system (2019): relation
tuples `(object, relation, subject)` plus rewrite rules, which is to
say a Datalog program at planetary scale. SpiceDB and OpenFGA are its
open-source descendants. *(Lesson 20)*
