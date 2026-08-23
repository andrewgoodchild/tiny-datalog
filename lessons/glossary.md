# Glossary

Every technical term the course uses, with the lesson that introduces
it. Alphabetical, so you can arrive here from anywhere.

---

**ABox** — the assertional part of a knowledge base: statements about
*individuals* ("bob is a Father"). Contrast **TBox**. `subsumption.py`
has no ABox at all; it reasons only about definitions. *(Lesson 10)*

**Absorption** — the semiring law `A + A·B = A`: a witness set that
contains another is discarded as redundant. It is what makes
why-provenance a *quotient* of the provenance polynomial, and therefore
lossy. *(Lesson 6)*

**Adornment** — a string of `b`/`f` marking which arguments of a
predicate are bound (known) or free at call time. `path#bf` is "path,
called with the first argument known". The bookkeeping magic sets runs
on. *(Lesson 4)*

**Aggregation** — collapsing many body solutions into one value:
`sum`, `count`, `min`, `max`. Written in the rule head,
`total(P, sum(A)) :- charge(P, C, A).`, where the remaining head
arguments are the implicit GROUP BY. *(Lesson 12)*

**Alternating fixpoint** — Van Gelder's method for computing the
well-founded model: iterate the (antimonotone) Gelfond–Lifschitz
operator twice, which is monotone, and read the undefined atoms off the
gap between the result and its image. *(Lesson 5)*

**Answer Set Programming (ASP)** — the branch of logic programming
where a program is written so that its **stable models** *are* the
solutions to a combinatorial problem. `clingo` is the standard
implementation. *(Lessons 0, 5)*

**Arity** — the number of arguments a predicate takes. `path/2` means
`path` with arity 2. This engine requires arity to be consistent across
a program. *(Lesson 1)*

**Atom** — a predicate applied to terms: `parent(abe, bob)` or
`path(X, Y)`. A **ground** atom has no variables. *(Lesson 1)*

**Base fact** — see **EDB**.

**Body** — the part of a rule to the right of `:-`, a conjunction of
literals. The **head** is to the left. *(Lesson 1)*

**Bottom-up evaluation** — start from the facts and apply rules
forwards until nothing new appears. What `datalog.py` does. Contrast
**top-down**. *(Lesson 2)*

**Chandra–Merlin theorem** — for conjunctive queries, Q2 contains Q1
iff there is a **homomorphism** from Q2's body into Q1's body fixing
the head variables. Turns a question about infinitely many databases
into a finite search. *(Lesson 14)*

**Chase** — the procedure for repairing a database against existential
rules by inventing witnesses. Not implemented here; it is where
Datalog± lives. *(Lesson 0)*

**Classification** — computing the full subsumption hierarchy of an
ontology, i.e. discovering where every concept belongs. KL-ONE's
signature feature. *(Lesson 10)*

**Closed-world assumption (CWA)** — absence means false: if a fact
cannot be derived, it is taken to be untrue. What makes negation
computable, and what makes missing data dangerous. Contrast **OWA**.
*(Lessons 3, 15)*

**Completion rules** — the saturation calculus that decides EL
subsumption (CR1–CR4 plus reflexivity). Monotone rules run to fixpoint,
which is why they compile to Datalog. *(Lesson 10)*

**Compound term** — a term with structure, like `s(N)` or
`cons(H, T)`. Also called a **function symbol** application. Datalog
bans them; `prolog.py` allows them. *(Lesson 9)*

**Conjunctive query** — a single rule with no negation and no
recursion: the SELECT–FROM–WHERE of Datalog. The fragment where
containment is decidable. *(Lesson 14)*

**Constant** — a value: `bob`, `42`, `"Mary Jane"`. Lowercase
identifiers, numbers, or quoted strings. *(Lesson 1)*

**Containment** — Q2 ⊇ Q1 means every answer to Q1 is an answer to Q2
*on every database*. **Equivalence** is containment both ways.
*(Lesson 14)*

**Datalog** — a query language of function-free Horn clauses evaluated
bottom-up. Declarative, recursive, and guaranteed to terminate.
*(Lesson 0)*

**Datalog°** — current research defining program semantics as a least
fixpoint in an *ordered semiring*, characterising when convergence and
semi-naive evaluation still hold. *(Lesson 6)*

**DBSP** — the algebraic foundation for incremental computation (VLDB
2023), generalising semi-naive evaluation to arbitrary changes. The
Feldera engine implements it. *(Lesson 8)*

**Default reasoning** — "P holds unless something says otherwise", the
Tweety pattern: `flies(X) :- bird(X), not abnormal(X).` Requires CWA
and is therefore **non-monotone**. *(Lessons 3, 15)*

**Delta** — the set of facts newly derived in the previous round. The
central object of semi-naive evaluation and of incremental
maintenance. *(Lessons 2, 8)*

**Dependency graph** — predicates as nodes, "uses in a rule body" as
edges, labelled positive, negative, or aggregating. Stratification is a
question about its cycles. *(Lesson 3)*

**DRed (delete and rederive)** — the 1993 algorithm for deleting from a
materialised view: over-delete everything reachable from the removed
fact, then re-derive whatever still has support. *(Lesson 8)*

**EDB (extensional database)** — the predicates defined by facts, i.e.
your input data. Contrast **IDB**. *(Lesson 1)*

**EL** — the description logic of conjunction and existential
restriction, with polynomial-time subsumption. The tractable core
underneath OWL 2 EL. **EL++** and **ELH** add ⊥, role hierarchies and
right identities. *(Lesson 10)*

**Equivalence** — see **Containment**.

**Fact** — a rule with an empty body; a ground atom asserted outright.
*(Lesson 1)*

**Fixpoint** — a set unchanged by applying the rules again; the point
at which evaluation stops. The **least fixpoint** is the smallest such
set, and is what a Datalog program means. *(Lesson 2)*

**Function symbol** — see **Compound term**.

**Gelfond–Lifschitz reduct** — given a candidate model S, delete every
rule whose negated atoms are in S and strip the remaining negations.
What is left is negation-free; M is a **stable model** iff the reduct's
least model is exactly M. *(Lesson 5)*

**Ground** — containing no variables. A ground atom is a specific fact;
**grounding** a program means instantiating its rules over all
constants. *(Lessons 1, 5)*

**Head** — the atom to the left of `:-`, the conclusion a rule draws.
*(Lesson 1)*

**Herbrand universe / base** — the set of all constants in a program,
and all ground atoms buildable from them. Finite for Datalog, infinite
once function symbols appear — which is exactly why Datalog
terminates. *(Lesson 9)*

**Homomorphism** — a map from one structure's variables to another's
terms that sends every atom onto an atom. Finding one is what `_match`
does against a database, and what containment does against another
query body. *(Lesson 14)*

**Horn clause** — a formula with at most one positive literal, i.e.
exactly the shape `head :- body`. Datalog is Horn clauses without
function symbols. *(Lesson 9)*

**IDB (intensional database)** — the predicates defined by rules, i.e.
what the program derives. Contrast **EDB**. *(Lesson 1)*

**Idempotent** — an operation where `a + a = a`. Idempotent semirings
(min-plus, boolean) converge on cyclic programs where counting
diverges. *(Lesson 6)*

**Immediate consequence operator (T_P)** — the function taking a set of
facts to everything derivable from it in one step. Evaluation is
iterating it to a fixpoint. *(Lesson 2)*

**Incremental view maintenance** — updating derived relations after the
input changes, rather than recomputing. Insertions resume semi-naive;
deletions need **DRed**. *(Lesson 8)*

**Join** — combining two relations on shared variables. In this engine
a rule body *is* a join, performed by folding `_match` over its
literals under one growing substitution. *(Lesson 1)*

**Literal** — an atom, or a negated atom (`not p(X)`). *(Lesson 3)*

**Magic sets** — a program rewriting that makes bottom-up evaluation
goal-directed, by adding **magic predicates** recording which bindings
are actually demanded. *(Lesson 4)*

**Materialisation** — the stored result of evaluating a program; what
incremental maintenance keeps up to date. *(Lesson 8)*

**Minimisation** — finding the smallest rule body equivalent to the one
you wrote, by dropping atoms a homomorphism can repair. *(Lesson 14)*

**Model** — a set of facts satisfying every rule. The **least model**
is the smallest one, and is the meaning of a positive program.
*(Lessons 2, 5)*

**Monotone / non-monotone** — monotone means adding facts can only add
conclusions. Positive Datalog is monotone; negation and aggregation are
not, which is why both need stratification. *(Lessons 3, 12, 15)*

**Naive evaluation** — applying every rule to the whole database every
round, rediscovering everything each time. The baseline semi-naive
improves on; `--naive` runs it. *(Lesson 2)*

**Negation as failure** — `not p` succeeds when `p` cannot be derived.
Not classical negation: it is a statement about the database, not the
world. *(Lesson 3)*

**Occurs check** — refusing to unify `X` with a term containing `X`,
which would build an infinite term. `prolog.py` performs it; real
Prolog usually skips it for speed. *(Lesson 9)*

**Open-world assumption (OWA)** — absence means unknown: unstated facts
are neither true nor false. Description logics assume it; consequently
they are **monotone** and cannot express defaults. *(Lesson 15)*

**Predicate** — the name of a relation: `parent`, `path`, `eligible`.
*(Lesson 1)*

**Primitive vs defined concept** — `isa` states a *necessary*
condition; `define` states necessary **and sufficient** ones. Only
defined concepts can be *discovered* to sit beneath something nobody
stated. *(Lesson 10)*

**Provenance** — the record of *why* a fact holds. **Why-provenance**
gives minimal sets of base facts (**witnesses**); **provenance
polynomials** (ℕ[X]) additionally keep multiplicity and are the free
semiring, so everything else factors through them. *(Lesson 6)*

**QSQR** — Query-Subquery Recursive, the set-at-a-time top-down
evaluation strategy `tabling.py` implements. *(Lesson 13)*

**Range restriction** — see **Safety**.

**Recursion** — a predicate defined in terms of itself.
**Linear** recursion has one recursive body literal; **non-linear** has
several, which reaches the fixpoint in logarithmically many rounds.
**Left recursion** puts the recursive call first, which defeats SLD but
not tabling. *(Lessons 2, 13)*

**Role** — a binary relation in a description logic (`has_child`).
A **role hierarchy** relates roles to each other; not supported here.
*(Lesson 10)*

**Safety (range restriction)** — every variable in a rule head, and
every variable under `not`, must also appear in a positive body
literal. What keeps every derived relation finite. *(Lessons 1, 3)*

**Semi-naive evaluation** — re-joining rules only against the previous
round's **delta** rather than the whole database. The standard
bottom-up optimisation, and the ancestor of incremental view
maintenance. *(Lesson 2)*

**Semiring** — a set with `+` and `×`, each with an identity. Attach a
semiring value to every fact, multiply along a derivation and add
across derivations, and the same program computes reachability, cost,
counts, provenance, or probability. *(Lesson 6)*

**Sideways information passing (SIPS)** — the order in which bindings
flow through a rule body, determining the adornments magic sets
generates. Here it is simply left to right, matching the evaluator.
*(Lesson 4)*

**SLD resolution** — the top-down proof procedure of Prolog: unify the
goal with a rule head, then prove the body. Tuple-at-a-time, and
vulnerable to left recursion. **SLG** adds tabling. *(Lessons 9, 13)*

**Stable model** — a set of facts that justifies itself: the
Gelfond–Lifschitz reduct with respect to it derives exactly it. A
program may have one (determinate), none (contradictory), or several
(underspecified). *(Lesson 5)*

**Stratification** — partitioning predicates into **strata** so that
nothing depends on its own negation (or aggregation), then evaluating
stratum by stratum. Syntactic, decidable, and the condition this engine
enforces. *(Lessons 3, 12)*

**Strongly connected component (SCC)** — a maximal set of mutually
reachable nodes in the dependency graph. Every cycle lives inside one,
so stratifiability reduces to "no strict edge inside an SCC".
*(Lesson 3)*

**Subsumption** — C ⊑ D: every possible instance of C must be an
instance of D, in every world consistent with the definitions. A
statement about definitions, not data. *(Lesson 10)*

**Substitution** — a mapping from variables to values, built up while
matching a rule body. *(Lesson 1)*

**Tabling** — top-down evaluation that memoises each subgoal's answers
in a **table**, so recursive calls read the table instead of
descending. Gives Prolog-style goal direction with Datalog-style
termination. *(Lesson 13)*

**TBox** — the terminological part of a knowledge base: the definitions
themselves. Contrast **ABox**. *(Lesson 10)*

**Term** — a constant, a variable, or (outside Datalog) a compound
term. *(Lesson 1)*

**Top-down evaluation** — start from the query and work backwards to
the facts. Natively goal-directed; see **SLD resolution** and
**tabling**. *(Lessons 9, 13)*

**Unification** — making two terms equal by binding variables, where
*both* sides may contain variables. Matching against a ground database
is the one-way special case. *(Lesson 9)*

**Variable** — a placeholder, written with an initial capital or
underscore: `X`, `Cook`, `_`. *(Lesson 1)*

**Viterbi semiring** — (max, ×) over [0,1]: the probability of the most
likely single derivation. A genuine semiring, unlike "total
probability", which is not. *(Lesson 7)*

**Well-founded semantics** — a three-valued semantics (true, false,
**undefined**) that always exists, settling what it can and naming what
is genuinely circular. *(Lesson 5)*

**Witness** — a minimal set of base facts sufficient to derive a
conclusion; why-provenance returns the set of them. *(Lesson 6)*
