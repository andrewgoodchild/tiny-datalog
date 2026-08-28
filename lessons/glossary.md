# Glossary

Every technical term the course uses, with the lesson that introduces
it. Alphabetical, so you can arrive here from anywhere.

---

**ABox.** The assertional part of a knowledge base: statements about
*individuals* ("bob is a Father"). Contrast **TBox**. `subsumption.py`
has no ABox at all; it reasons only about definitions. *(Lesson 11)*

**Absorption.** The semiring law `A + A·B = A`: a witness set that
contains another is discarded as redundant. It is what makes
why-provenance a *quotient* of the provenance polynomial, and therefore
lossy. *(Lesson 7)*

**Adornment.** A string of `b`/`f` marking which arguments of a
predicate are bound (known) or free at call time. `path#bf` is "path,
called with the first argument known". The bookkeeping magic sets runs
on. *(Lesson 6)*

**Aggregation.** Collapsing many body solutions into one value:
`sum`, `count`, `min`, `max`. Written in the rule head,
`total(P, sum(A)) :- charge(P, C, A).`, where the remaining head
arguments are the implicit GROUP BY. *(Lesson 13)*

**Alternating fixpoint.** Van Gelder's method for computing the
well-founded model: iterate the (antimonotone) Gelfond–Lifschitz
operator twice, which is monotone, and read the undefined atoms off the
gap between the result and its image. *(Lesson 5)*

**Answer Set Programming (ASP).** The branch of logic programming
where a program is written so that its **stable models** *are* the
solutions to a combinatorial problem. `clingo` is the standard
implementation. *(Lessons 0, 5)*

**Arity.** The number of arguments a predicate takes. `path/2` means
`path` with arity 2. This engine requires arity to be consistent across
a program. *(Lesson 1)*

**Atom.** A predicate applied to terms: `parent(abe, bob)` or
`path(X, Y)`. A **ground** atom has no variables. *(Lesson 1)*

**Backward/Forward (B/F).** The 2015 deletion algorithm (Motik, Nenov,
Piro, Horrocks; implemented in RDFox): compute the facts affected by a
deletion, then confirm each by backward chaining for an alternative,
well-founded derivation before removing anything. The check-first
counterpart to **DRed**'s demolish-first. *(Lesson 9)*

**Base fact.** See **EDB**.

**BFS (breadth-first search).** Explore a graph level by level. Used
here only to reconstruct the shortest offending cycle when
stratification fails. *(Lesson 12)*

**Body.** The part of a rule to the right of `:-`, a conjunction of
literals. The **head** is to the left. *(Lesson 1)*

**Bottom-up evaluation.** Start from the facts and apply rules
forwards until nothing new appears. What `datalog.py` does. Contrast
**top-down**. *(Lesson 2)*

**CALM theorem.** Consistency As Logical Monotonicity: a distributed
program can be run without coordination exactly when it is monotone,
which for Datalog means negation-free. *(Lesson 0)*

**Canonical instance.** A query's own body, with its variables frozen
into fresh constants: the smallest, most hostile database satisfying
the query. Testing against it stands in for testing against all
databases (Chandra–Merlin). *(Lesson 15)*

**Chandra–Merlin theorem.** For conjunctive queries, Q2 contains Q1
iff there is a **homomorphism** from Q2's body into Q1's body fixing
the head variables. Turns a question about infinitely many databases
into a finite search. *(Lesson 15)*

**Chase.** The procedure for repairing a database against existential
rules by inventing witnesses. Not implemented here; it is where
Datalog± lives. *(Lesson 0)*

**Classification.** Computing the full subsumption hierarchy of an
ontology, i.e. discovering where every concept belongs. KL-ONE's
signature feature. *(Lesson 11)*

**Closed-world assumption (CWA).** Absence means false: if a fact
cannot be derived, it is taken to be untrue. What makes negation
computable, and what makes missing data dangerous. Contrast **OWA**.
*(Lessons 3, 4)*

**Combined complexity.** Cost when both the rules and the data are
allowed to vary. Datalog is EXPTIME-complete here, and the exponential
lives in the number of variables per rule. Contrast **data
complexity**. *(Lesson 2)*

**Completion rules.** The saturation calculus that decides EL
subsumption (CR1–CR4 plus reflexivity). Monotone rules run to fixpoint,
which is why they compile to Datalog. *(Lesson 11)*

**Compound term.** A term with structure, like `s(N)` or
`cons(H, T)`. Also called a **function symbol** application. Datalog
bans them; `prolog.py` allows them. *(Lesson 10)*

**Conjunctive query.** A single rule with no negation and no
recursion: the SELECT–FROM–WHERE of Datalog. The fragment where
containment is decidable. *(Lesson 15)*

**Constant.** A value: `bob`, `42`, `"Mary Jane"`. Lowercase
identifiers, numbers, or quoted strings. *(Lesson 1)*

**Containment.** Q2 ⊇ Q1 means every answer to Q1 is an answer to Q2
*on every database*. **Equivalence** is containment both ways.
*(Lesson 15)*

**DAG (directed acyclic graph).** A directed graph with no cycles.
Transitive closure over one always terminates quickly; the interesting
cases in this course are the graphs that are *not* acyclic. *(Lesson 7)*

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
semi-naive evaluation still hold. *(Lesson 7)*

**DBSP.** The algebraic foundation for incremental computation (VLDB
2023): programs become circuits over **Z-sets**, every operator gets a
uniform derivative, and insertion and deletion stop being different
algorithms. Generalises semi-naive evaluation to arbitrary changes; the
Feldera engine implements it, programmed in SQL. *(Lesson 9)*

**Decidable.** A question a terminating procedure can always answer.
Datalog is built out of deliberate restrictions that keep questions
decidable: termination, stratifiability, and containment for
non-recursive queries are all decidable, and each becomes
**undecidable** just outside the fence. *(Lessons 3, 10, 15)*

**Default reasoning.** "P holds unless something says otherwise", the
Tweety pattern: `flies(X) :- bird(X), not abnormal(X).` Requires CWA
and is therefore **non-monotone**. *(Lessons 3, 4)*

**Delta.** The set of facts newly derived in the previous round. The
central object of semi-naive evaluation and of incremental
maintenance. *(Lessons 2, 9)*

**Dependency graph.** Predicates as nodes, "uses in a rule body" as
edges, labelled positive, negative, or aggregating. Stratification is a
question about its cycles. *(Lesson 3)*

**DRed (delete and rederive).** The 1993 algorithm for deleting from a
materialised view: over-delete everything reachable from the removed
fact, then re-derive whatever still has support. Contrast
**Backward/Forward**, which checks before deleting. *(Lesson 9)*

**EDB (extensional database).** The predicates defined by facts, i.e.
your input data. Contrast **IDB**. *(Lesson 1)*

**EL.** The description logic of conjunction and existential
restriction, with polynomial-time subsumption. The tractable core
underneath OWL 2 EL. **EL++** and **ELH** add ⊥, role hierarchies and
right identities. *(Lesson 11)*

**Equivalence.** See **Containment**.

**Fact.** A rule with an empty body; a ground atom asserted outright.
*(Lesson 1)*

**Fixpoint.** A set unchanged by applying the rules again; the point
at which evaluation stops. The **least fixpoint** is the smallest such
set, and is what a Datalog program means. *(Lesson 2)*

**Free object.** An algebraic structure satisfying only the equations
it must: any assignment of its generators into another structure of
the same kind extends to exactly one homomorphism. The provenance
polynomials ℕ[X] are the free commutative semiring, which is why every
semiring's answer factors through them. *(Lesson 7)*

**Function symbol.** See **Compound term**.

**Functor.** A structure-preserving map between categories. In CQL a
database instance *is* a functor from the schema to sets, so violating
a constraint means failing to be an instance at all. *(Lesson 17)*

**Gelfond–Lifschitz reduct.** Given a candidate model S, delete every
rule whose negated atoms are in S and strip the remaining negations.
What is left is negation-free; M is a **stable model** iff the reduct's
least model is exactly M. *(Lesson 5)*

**Ground.** Containing no variables. A ground atom is a specific fact;
**grounding** a program means instantiating its rules over all
constants. *(Lessons 1, 5)*

**Head.** The atom to the left of `:-`, the conclusion a rule draws.
*(Lesson 1)*

**Herbrand universe / base.** The set of all constants in a program,
and all ground atoms buildable from them. Finite for Datalog, infinite
once function symbols appear, which is exactly why Datalog
terminates. *(Lesson 10)*

**Homomorphism.** A map from one structure's variables to another's
terms that sends every atom onto an atom. Finding one is what `_match`
does against a database, and what containment does against another
query body. *(Lesson 15)*

**Horn clause.** A formula with at most one positive literal, i.e.
exactly the shape `head :- body`. Datalog is Horn clauses without
function symbols. *(Lesson 10)*

**IDB (intensional database).** The predicates defined by rules, i.e.
what the program derives. Contrast **EDB**. *(Lesson 1)*

**Idempotent.** An operation where `a + a = a`. Idempotent semirings
(min-plus, boolean) converge on cyclic programs where counting
diverges. *(Lesson 7)*

**Immediate consequence operator (T_P).** The function taking a set of
facts to everything derivable from it in one step. Evaluation is
iterating it to a fixpoint. *(Lesson 2)*

**Incremental view maintenance.** Updating derived relations after the
input changes, rather than recomputing. Insertions resume semi-naive;
deletions need **DRed**. *(Lesson 9)*

**Join.** Combining two relations on shared variables. In this engine
a rule body *is* a join, performed by folding `_match` over its
literals under one growing substitution. *(Lesson 1)*

**Kan extension.** Category theory's universal way of extending a
functor along another; CQL's data-migration operators Σ and Π are the
left and right Kan extensions, and the chase computes the left one.
*(Lesson 17)*

**Knaster–Tarski theorem.** A monotone function on a complete lattice
has a least fixpoint. Applied to the immediate consequence operator on
the (finite) powerset lattice of facts, it is the two-line reason every
Datalog program terminates with a unique meaning. *(Lesson 2)*

**Labelled null.** Database theory's honest unknown: an invented
witness ("someone, unspecified") that is *self-identical* across
occurrences, unlike SQL's NULL. Produced by the chase for existential
rules; `subsumption.py`'s `gen_N` names are miniature ones. *(Lessons
4, 17)*

**Lattice.** A partially ordered set where any two elements have a
meet and a join; here, all possible fact-sets ordered by ⊆. The stage
on which Knaster–Tarski performs. *(Lesson 2)*

**Literal.** An atom, or a negated atom (`not p(X)`). *(Lesson 3)*

**Magic sets.** A program rewriting that makes bottom-up evaluation
goal-directed, by adding **magic predicates** recording which bindings
are actually demanded. *(Lesson 6)*

**Materialisation.** The stored result of evaluating a program; what
incremental maintenance keeps up to date. *(Lesson 9)*

**Minimisation.** Finding the smallest rule body equivalent to the one
you wrote, by dropping atoms a homomorphism can repair. *(Lesson 15)*

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
Prolog usually skips it for speed. *(Lesson 10)*

**Open-world assumption (OWA).** Absence means unknown: unstated facts
are neither true nor false. Description logics assume it; consequently
they are **monotone** and cannot express defaults. *(Lesson 4)*

**Predicate.** The name of a relation: `parent`, `path`, `eligible`.
*(Lesson 1)*

**Primitive vs defined concept.** `isa` states a *necessary*
condition; `define` states necessary **and sufficient** ones. Only
defined concepts can be *discovered* to sit beneath something nobody
stated. *(Lesson 11)*

**Provenance.** The record of *why* a fact holds. **Why-provenance**
gives minimal sets of base facts (**witnesses**); **provenance
polynomials** (ℕ[X]) additionally keep multiplicity and are the free
semiring, so everything else factors through them. *(Lesson 7)*

**PTIME-complete.** As hard as any problem solvable in polynomial
time, so (barring a complexity-theoretic surprise) inherently
sequential: not parallelisable to polylogarithmic time. Datalog's data
complexity is PTIME-complete, which is a statement about its power as
well as its cost. *(Lesson 2)*

**QSQR.** Query-Subquery Recursive, the set-at-a-time top-down
evaluation strategy `tabling.py` implements. *(Lesson 14)*

**Range restriction.** See **Safety**.

**Recursion.** A predicate defined in terms of itself.
**Linear** recursion has one recursive body literal; **non-linear** has
several, which reaches the fixpoint in logarithmically many rounds.
**Left recursion** puts the recursive call first, which defeats SLD but
not tabling. *(Lessons 2, 14)*

**Role.** A binary relation in a description logic (`has_child`).
A **role hierarchy** relates roles to each other; not supported here.
*(Lesson 11)*

**Safety (range restriction).** Every variable in a rule head, and
every variable under `not`, must also appear in a positive body
literal. What keeps every derived relation finite. *(Lessons 1, 3)*

**Semi-naive evaluation.** Re-joining rules only against the previous
round's **delta** rather than the whole database. The standard
bottom-up optimisation, and the ancestor of incremental view
maintenance. *(Lesson 2)*

**Semiring.** A set with `+` and `×`, each with an identity. Attach a
semiring value to every fact, multiply along a derivation and add
across derivations, and the same program computes reachability, cost,
counts, provenance, or probability. *(Lesson 7)*

**Sideways information passing (SIPS).** The order in which bindings
flow through a rule body, determining the adornments magic sets
generates. Here it is simply left to right, matching the evaluator.
*(Lesson 6)*

**SLD resolution.** The top-down proof procedure of Prolog: unify the
goal with a rule head, then prove the body. Tuple-at-a-time, and
vulnerable to left recursion. **SLG** adds tabling. *(Lessons 10, 14)*

**Stable model.** A set of facts that justifies itself: the
Gelfond–Lifschitz reduct with respect to it derives exactly it. A
program may have one (determinate), none (contradictory), or several
(underspecified). *(Lesson 5)*

**Stratification.** Partitioning predicates into **strata** so that
nothing depends on its own negation (or aggregation), then evaluating
stratum by stratum. Syntactic, decidable, and the condition this engine
enforces. *(Lessons 3, 13)*

**Strongly connected component (SCC).** A maximal set of mutually
reachable nodes in the dependency graph. Every cycle lives inside one,
so stratifiability reduces to "no strict edge inside an SCC".
*(Lesson 3)*

**Substitution.** A mapping from variables to values, built up while
matching a rule body. *(Lesson 1)*

**Subsumption.** C ⊑ D: every possible instance of C must be an
instance of D, in every world consistent with the definitions. A
statement about definitions, not data. *(Lesson 11)*

**Tabling.** Top-down evaluation that memoises each subgoal's answers
in a **table**, so recursive calls read the table instead of
descending. Gives Prolog-style goal direction with Datalog-style
termination. *(Lesson 14)*

**TBox.** The terminological part of a knowledge base: the definitions
themselves. Contrast **ABox**. *(Lesson 11)*

**Term.** A constant, a variable, or (outside Datalog) a compound
term. *(Lesson 1)*

**Top-down evaluation.** Start from the query and work backwards to
the facts. Natively goal-directed; see **SLD resolution** and
**tabling**. *(Lessons 10, 14)*

**Undecidable.** No terminating procedure can answer it in general.
Whether an arbitrary Horn-clause program halts (Lesson 10), and whether
one *recursive* Datalog program contains another (Shmueli 1993, Lesson
15), are both undecidable, which is precisely why this engine bans
function symbols and `containment.py` refuses recursion. *(Lessons 10, 15)*

**Unification.** Making two terms equal by binding variables, where
*both* sides may contain variables. Matching against a ground database
is the one-way special case. *(Lesson 10)*

**Variable.** A placeholder, written with an initial capital or
underscore: `X`, `Cook`, `_`. *(Lesson 1)*

**Viterbi semiring.** (max, ×) over [0,1]: the probability of the most
likely single derivation. A genuine semiring, unlike "total
probability", which is not. *(Lesson 8)*

**Well-founded semantics.** A three-valued semantics (true, false,
**undefined**) that always exists, settling what it can and naming what
is genuinely circular. *(Lesson 5)*

**Witness.** A minimal set of base facts sufficient to derive a
conclusion; why-provenance returns the set of them. *(Lesson 7)*

**Z-set.** A collection where each fact carries a signed integer
multiplicity: +1 is an insertion, −1 a deletion, and a change is data
flowing through the same operators as the facts themselves. The
representation underneath **DBSP**, and what plain sets cannot express
("this fact lost one of its two supports"). *(Lesson 9)*
