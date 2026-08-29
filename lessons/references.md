# References

Every work the lessons cite, by the lesson that cites it. Full titles
are given where they are canonical; where memory of an exact title is
less than certain, the entry is descriptive (author, year, venue,
result) — a citation is the one kind of claim this repository's
transcript checker cannot verify, so these err on the side of what can
be defended.

## Lesson 0 — history

- J. A. Robinson, *A Machine-Oriented Logic Based on the Resolution
  Principle*, JACM 1965.
- M. van Emden and R. Kowalski, *The Semantics of Predicate Logic as a
  Programming Language*, JACM 1976 — the least-model semantics.
- H. Gallaire and J. Minker (eds.), *Logic and Data Bases*, Plenum
  1978 — the workshop volume that convened the field.
- D. Maier, D. S. Warren and colleagues, *Datalog: Concepts, History,
  and Outlook*, 2018 (in *Declarative Logic Programming*, ACM Books) —
  the retrospective by the people who lived it.
- Whaley and Lam's bddbddb (2004) and Bravenboer and Smaragdakis's
  Doop (OOPSLA 2009) — the program-analysis line; descriptive.
- The CALM theorem: Hellerstein and Alvaro's line of work on
  consistency as logical monotonicity; descriptive.

## Lesson 2 — fixpoints

- B. Knaster and A. Tarski — the fixpoint theorem the lesson names;
  Tarski's general lattice form is *A Lattice-Theoretical Fixpoint
  Theorem and its Applications*, Pacific J. Math. 1955.

## Lesson 4 — closed and open worlds

- R. Reiter, *On Closed World Data Bases*, in Gallaire and Minker
  1978 — the CWA, named in the field's founding volume.

## Lesson 5 — stable models

- M. Gelfond and V. Lifschitz, *The Stable Model Semantics for Logic
  Programming*, ICLP/SLP 1988.
- A. Van Gelder, K. Ross and J. Schlipf, *The Well-Founded Semantics
  for General Logic Programs*, JACM 1991.
- B. Russell — the 1902 letter to Frege and the barber are standard
  history; any edition of *From Frege to Gödel* (van Heijenoort)
  carries the primary documents.
- T. Soininen and I. Niemelä, 1998 — answer set programming applied to
  product configuration; descriptive.
- D. Abels, J. Jordi, M. Ostrowski, T. Schaub, A. Toletti and
  P. Wanko, *Train Scheduling with Hybrid Answer Set Programming*,
  arXiv 2003.08598.

## Lesson 7 — magic sets and joins

- F. Bancilhon, D. Maier, Y. Sagiv and J. Ullman, *Magic Sets and
  Other Strange Ways to Implement Logic Programs*, PODS 1986.
- A. Atserias, M. Grohe and D. Marx — the AGM bound on join output
  size, FOCS 2008 (journal version SICOMP 2013).
- T. Veldhuizen, *Leapfrog Triejoin: A Simple, Worst-Case Optimal Join
  Algorithm*, ICDT 2014.

## Lesson 8 — semirings and provenance

- T. J. Green, G. Karvounarakis and V. Tannen, *Provenance Semirings*,
  PODS 2007.
- M. Abo Khamis, H. Ngo, D. Suciu and colleagues — the Datalog°
  convergence line, 2022 onward; descriptive.
- H. S. Vandiver, 1934, Bull. AMS — the note on algebra without
  additive cancellation usually credited with the word "semiring".

## Lesson 9 — probabilistic

- A. Viterbi, *Error Bounds for Convolutional Codes and an
  Asymptotically Optimum Decoding Algorithm*, IEEE Trans. Information
  Theory 1967.
- Scallop — differentiable Datalog over provenance semirings, PLDI
  2023; descriptive.

## Lesson 10 — incremental maintenance

- A. Gupta, I. S. Mumick and V. S. Subrahmanian, *Maintaining Views
  Incrementally*, SIGMOD 1993 — DRed.
- B. Motik, Y. Nenov, R. Piro and I. Horrocks, *Incremental Update of
  Datalog Materialisation: the Backward/Forward Algorithm*, AAAI 2015.
- M. Budiu, T. Chajed, F. McSherry, L. Ryzhyk and V. Tannen, *DBSP:
  Automatic Incremental View Maintenance for Rich Query Languages*,
  VLDB 2023.

## Lesson 11 — Horn clauses

- A. Horn, *On Sentences Which are True of Direct Unions of Algebras*,
  J. Symbolic Logic 1951.

## Lesson 12 — description logics

- R. Brachman, 1977 — the Harvard dissertation on structured
  inheritance networks that became KL-ONE; descriptive.
- R. Brachman and J. Schmolze, *An Overview of the KL-ONE Knowledge
  Representation System*, Cognitive Science 1985.
- R. Brachman and H. Levesque, *The Tractability of Subsumption in
  Frame-Based Description Languages*, AAAI 1984.
- M. Schmidt-Schauß, *Subsumption in KL-ONE is Undecidable*, KR 1989.
- F. Baader, *Terminological Cycles in a Description Logic with
  Existential Restrictions*, IJCAI 2003.
- F. Baader, S. Brandt and C. Lutz, *Pushing the EL Envelope*,
  IJCAI 2005.
- T. Gruber, *A Translation Approach to Portable Ontology
  Specifications*, Knowledge Acquisition 1993 — "an explicit
  specification of a conceptualization".
- M. Kifer and G. Lausen, *F-Logic: A Higher-Order Language for
  Reasoning about Objects, Inheritance, and Scheme*, SIGMOD 1989;
  the full treatment is Kifer, Lausen and Wu, JACM 1995.

## Lesson 13 — aggregation and lattices

- Flix (Madsen, Yee and Lhoták, PLDI 2016) extends Datalog with
  user-defined lattices; Datafun and IncA are kindred designs;
  descriptive. DRedL is the incremental-lattice-maintenance line;
  descriptive.

## Lesson 14 — arithmetic

- Constrained Horn clauses as the verification interface: the CHC-COMP
  competition and Z3's Spacer engine; descriptive.

## Lesson 16 — containment and views

- A. Chandra and P. Merlin, *Optimal Implementation of Conjunctive
  Queries in Relational Data Bases*, STOC 1977.
- O. Shmueli — undecidability of containment and equivalence for
  recursive Datalog; FOCS 1987, with the journal treatment in
  J. Logic Programming 1993.
- A. Halevy, *Answering Queries Using Views: A Survey*, VLDB
  Journal 2001.

## Lesson 18 — category theory

- S. Eilenberg and S. Mac Lane, *General Theory of Natural
  Equivalences*, Trans. AMS 1945.
- D. Spivak, *Functorial Data Migration*, Information and
  Computation 2012; with R. Wisnesky, the CQL line of work;
  descriptive.

## Elsewhere

- W. Merrill and A. Sabharwal, *The Expressive Power of Transformers
  with Chain of Thought*, ICLR 2024 (arXiv 2310.07923) — cited in
  Lesson 0's discussion of what reasoning in tokens costs.
