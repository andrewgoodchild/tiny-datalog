# tiny-datalog

**A logic engine small enough to read in an afternoon, and a course
that builds it up from nothing.**

Here is a question you cannot answer by reading your own data.

You deploy 12 services. They sit on 160 packages joined by 292
dependency edges — each one individually boring, all of them together
past what anyone holds in their head. A CVE lands on one package. Which
services are exposed?

The 292 edges you wrote down imply **8,457** reachability facts. The
answer is in those, not in the edges, and being 95% right means
shipping a service you believed was clean.

Three rules compute it:

```prolog
% programs/00-supply-chain.dl
uses(X, Y) :- depends(X, Y).
uses(X, Z) :- depends(X, Y), uses(Y, Z).      % ... at any depth

exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).
```

`:-` means "if", the comma means "and", capitals are variables. The
second rule is the whole trick: a package uses whatever its
dependencies use, applied over and over until nothing new appears.

```
$ python3 datalog.py -q 'exposed(S, C)' programs/00-supply-chain.dl
?- exposed(S, C)
   exposed(pkg0, cve_2026_0001).
   exposed(pkg4, cve_2026_0001).
   exposed(pkg5, cve_2026_0001).
   exposed(pkg8, cve_2026_0001).
   (4 answers)
```

Four of twelve — and nothing in the input told you which four.

## Then the questions you actually have next

**"Why pkg4? I need to tell the team what to bump."**

```
$ python3 datalog.py --explain 'exposed(pkg4, cve_2026_0001)' programs/00-supply-chain.dl
?- explain exposed(pkg4, cve_2026_0001)
   exposed(pkg4, cve_2026_0001)   [via exposed(S, C) :- service(S), uses(S, L), vulnerable(L, C).]
     service(pkg4)   (base fact)
     uses(pkg4, pkg21)   [via uses(X, Z) :- depends(X, Y), uses(Y, Z).]
       depends(pkg4, pkg13)   (base fact)
       uses(pkg13, pkg21)   [via uses(X, Y) :- depends(X, Y).]
         depends(pkg13, pkg21)   (base fact)
     vulnerable(pkg21, cve_2026_0001)   (base fact)
```

pkg4 → pkg13 → pkg21. That is not an explanation *about* the answer,
it is the derivation the answer came out of — so it cannot be
plausible-but-wrong, and it is what you paste into the ticket.

**"Another CVE just dropped. Do I rerun everything?"**

No. The engine keeps the 8,457 facts and repairs them:

```python
>>> inc.insert("vulnerable(pkg40, cve_2026_0002).")
{'inserted': 1, 'derived': 12}        # 0.03s, against 0.81s to rebuild
```

Twelve new facts, and this CVE turns out to reach **all twelve
services** — which, again, nobody predicted by looking.

**"Is my policy even coherent?"** A different question again, and the
engine answers it: given rules that refer to their own conclusions, it
will tell you they have no consistent answer, or that they have several
and you have not said which one you meant. That is
[lesson 5](lessons/05-beyond-stratification.md), worked through on a
benefits policy in `programs/00-eligibility.dl`.

## Should you just ask a model instead?

For seven facts, yes. For this, the evidence is unusually clear, and it
does not say what a Datalog partisan would want it to say.

**The problem class is provably outside what a transformer does in
context.** Directed graph reachability is NL-complete and Horn-clause
satisfiability — which is what evaluating these rules *is* — is
P-complete. [Merrill and Sabharwal (ICLR 2024)](https://arxiv.org/abs/2310.07923)
prove that transformers with a linear number of chain-of-thought steps
cannot solve either, naming both explicitly. You would need roughly
O(n²) reasoning tokens to walk the graph.

**Measured, that shows up as a monotone slide.**
[GraphGym (2026)](https://arxiv.org/abs/2608.12391) ran 202 graph tasks
at n = 10 / 100 / 1,000 / 10,000. Reasoning in natural language:
**66.7 → 38.8 → 19.8 → 10.4** exact match. On pure transitive chains
with surface cues stripped out,
[NLGraph](https://arxiv.org/abs/2305.10037) found chain-of-thought
connectivity at **40.8% — below the 50% coin flip**. And when default
negation sits inside a recursive cycle — the case
[lesson 5](lessons/05-beyond-stratification.md) is about —
[ASPBench (2025)](https://arxiv.org/abs/2507.19749) finds every model
plateaus near 0.60 regardless of size or reasoning training.

**But here is the finding that actually matters, and it argues for a
pairing rather than a winner.** In that same GraphGym sweep, models
that *wrote code and ran it against the graph on disk* scored
**77.7 → 74.3 → 71.4 → 46.3** — the size-scaling cliff mostly
disappears. Much of the apparent reasoning failure is really that a
model cannot reliably transcribe a graph out of its own context window:
extraction accuracy from an in-context serialisation measured 54.5%.

So the honest conclusion is not that models cannot reason. It is that
**this computation belongs outside the context window**, and the model's
job is to write the rules, not to run them. Which is the pairing this
repository is built for: let a model turn a policy document into
Datalog, and let the engine decide what follows from it — exactly,
repeatably, with the derivation attached.

## What's in here

The evaluator that answers all of the above is about 800 lines of
dependency-free Python — genuinely an afternoon's read — surrounded by
eight modules that each add one classical technique, and a 16-lesson
course that builds the whole thing up from facts and rules.

If Datalog is new to you, read
[lesson 0](lessons/00-what-is-datalog.md) first: what it is, where it
came from, and why sound inference is worth more rather than less in
the age of language models. If a term here is unfamiliar,
[the glossary](lessons/glossary.md) defines every one the course uses.

## What you can ask it

Clone it and every row below runs — no dependencies, no install step,
Python 3.9+. This table is the quick start and the table of contents at
once: a question, the command that answers it, and the lesson that
builds it.

```sh
git clone https://github.com/<you>/tiny-datalog && cd tiny-datalog
python3 tests.py        # 119 tests, ~0.7s
```

| Question | Command | Lesson |
|---|---|---|
| What follows from these facts and rules? | `datalog.py programs/01-family.dl` | 1 |
| What's reachable, at any depth? | `datalog.py --trace programs/02-reachability.dl` | 2 |
| What holds *unless* something else does? | `datalog.py programs/03-tweety.dl` | 3 |
| Answer just this query — don't compute everything | `datalog.py --magic -q 'path(n5, X)' programs/02-reachability.dl` | 4 |
| Is this rule set self-contradictory? | `datalog.py --models programs/00-eligibility-paradox.dl` | 5 |
| Why did you conclude that? | `datalog.py --explain 'eligible(bob)' programs/00-eligibility.dl` | 1, 11 |
| Which facts does the conclusion rest on? | `semiring.py -s why programs/06-routes.dl` | 6 |
| What's the cheapest route? How many ways? | `semiring.py -s minplus programs/06-routes.dl` | 6 |
| How likely is it? | `semiring.py -s viterbi programs/07-prob-reach.dl` | 7 |
| The data changed — what changed in the answers? | `incremental.py programs/08-dred-graph.dl -u 'edge(n3, n4)~.'` | 8 |
| How many, how much, largest? | `datalog.py programs/12-spending.dl` | 12 |
| Answer a goal top-down, even left-recursive | `tabling.py programs/13-left-recursive.dl -q 'ancestor(abe, X)'` | 13 |
| What if I allow function symbols — and lose termination? | `prolog.py programs/09-peano.pl -q 'add(X, Y, s(s(zero)))'` | 9 |
| What do these definitions entail about each other? | `subsumption.py programs/10-family-ontology.dl` | 10 |
| Are these two queries the same query? | `containment.py programs/14-minimise.dl` | 14 |

Provenance, in full:

```
$ python3 semiring.py --semiring why -q 'path(a, d)' programs/06-routes.dl
path(a, d) = {edge(a, b), edge(b, c), edge(c, d)} | {edge(a, b), edge(b, d)} | {edge(a, c), edge(c, d)}
```

Three independent derivations, each a minimal set of base facts. Remove
one fact from a witness and that witness fails; remove all three and the
conclusion goes away. That is an audit trail computed rather than
narrated.

## Claims you can check

Every performance claim in the lessons is reproducible from the shipped
generator, including the one that goes the wrong way.

```sh
python3 benchmarks/generate.py chain 150 > chain150.dl
```

| Claim | How to check | Measured here |
|---|---|---|
| Semi-naive beats naive... | `--naive` vs default, chain-50 | 0.7s → 0.07s (**10×**) |
| ...and the gap grows with depth | `--naive` vs default, chain-100 | 10.8s → 0.23s (**47×**) |
| Magic sets makes a *selective* query goal-directed | `--magic -q 'path(n140, X)'`, chain-150 | **66 facts vs 11,175; 0.05s vs 0.62s** |
| Magic sets is not a free lunch | `--magic -q 'path(n1, X)'`, chain-150 | **11,325 facts vs 11,175; 2.19s vs 0.62s** |

The last two rows are the same rewriting on the same program, and they
are the honest pair. Magic sets pays off in proportion to how much the
query's bindings actually prune: ask from the far end of a chain and
demand stays local — 170× fewer facts and 12× faster. Ask from the near
end and demand propagates the chain's whole length, so the rewritten
program derives *more* facts than the original and pays a guard literal
on every join. Nested-loop joins amplify that overhead — each magic guard is a scan
rather than a lookup, which an index would fix — but the governing
variable is demand, not indexing. [Lesson 4](lessons/04-magic-sets.md) works through why.

Correctness claims are checked too, by a seeded differential fuzzer
(`DifferentialFuzzTests`) that generates stratified programs and demands
that semi-naive, naive, magic-sets and tabled evaluation agree on every
query, and that incremental maintenance matches from-scratch
recomputation under random insert/delete sequences. 400 programs per
test run; `TINY_DATALOG_FUZZ=3000 python3 tests.py DifferentialFuzzTests`
for a real soak.

## Learning Datalog

`lessons/` is a complete course — no prior exposure assumed, every
example a runnable file, following the field's own history from 1977 to
the current research threads. The Lesson column above is the index;
[lessons/getting-started.md](lessons/getting-started.md) has the titles
and the reading order, and
[lessons/glossary.md](lessons/glossary.md) defines every technical term
the course uses.

Every lesson ends with exercises, and every exercise has a worked answer
in `exercises/` — runnable where the answer is a program, and executed
by the test suite so the answers cannot rot. `cases/` lets anyone add a
regression test without writing Python.

## Where these techniques ship

Static analysis at scale (CodeQL, Soufflé) is Datalog. Knowledge graphs
(RDFox) are Datalog. Incremental view maintenance (Feldera) is the 1993
DRed paper with thirty years of engineering on top.
[Lesson 0](lessons/00-what-is-datalog.md) maps every technique in the
course to where it ships.

## What this is not

An engine to build a product on. Joins are nested-loop, stable-model
search is exhaustive, evaluation is batch. For real workloads see
Soufflé (static analysis), clingo (answer set programming), RDFox
(knowledge graphs), or Feldera (incremental).

The code favours readability over speed, the algorithms are the textbook
ones, and the error messages try to teach.

## Deliberately missing

Some absences are design decisions, and saying why teaches more than
quietly lacking them would:

- **Arithmetic and comparisons** (`X + 1`, `X < Y`). A built-in isn't a
  relation you can enumerate — `less_than` has infinitely many rows — so
  it must be *evaluated* at the moment its operands become bound. That
  entangles correctness with join order, which this engine keeps
  deliberately naive, and expressions force terms to become trees (the
  function-symbol boundary again, from the inside). The principled route
  is semantic attachments: a handler answering ground goals like
  `lt(3, 7)` on demand. Building one is a good exercise.
- **Indexes and join planning.** Every join is a nested loop on purpose:
  the algorithms stay one-screen readable, and the gap to Soufflé's
  compiled indexed joins is
  [lesson 11](lessons/11-under-the-hood.md)'s honest-limits discussion,
  not an accident.
- **⊤, ⊥, role hierarchies and right identities** in the classifier.
  What ships is plain EL. SNOMED CT needs ELH with right identities —
  the extension ELK and Snorocket implement — so this classifier
  demonstrates the calculus SNOMED-scale reasoners are built on without
  being able to classify SNOMED itself. The completion-rule approach
  generalises; these five rules do not cover it.
- **A REPL and packaging.** Files and flags keep every example
  reproducible from the shell, and zero packaging means the whole thing
  is `git clone` + `python3`.

Aggregation used to be on this list;
[lesson 12](lessons/12-aggregation.md) is what it looks like to promote
an omission into a feature without breaking the design.

## Layout

```
datalog.py      the core: AST, parser, safety checks, stratification,
                the semi-naive evaluator, and the CLI
magic.py        the magic-sets rewriting (a program-to-program pass)
semantics.py    grounding, stable models, the well-founded model
semiring.py     semiring-valued evaluation (costs, counts, provenance,
                probabilities)
incremental.py  insertions + DRed deletions over a live materialisation
prolog.py       top-down SLD resolution with function symbols
tabling.py      tabled top-down evaluation (iterative QSQR)
subsumption.py  KL-ONE-style EL classifier, compiled to Datalog
containment.py  query containment and minimisation by homomorphism
programs/       the classic teaching programs, numbered by lesson
lessons/        getting started, glossary, and lessons 0–15
exercises/      worked answers, verified by the test suite
cases/          golden test cases — add one without writing Python
benchmarks/     scaled input generators (chain/tree/clique/grid)
tests.py        119 tests: every shipped program and exercise answer is
                executed, a conformance suite runs every query through
                every applicable strategy, and a seeded fuzzer checks
                the same property on random programs
```

The code is part of the course: comments explain the algorithms as they
happen, and [lesson 11](lessons/11-under-the-hood.md) is the guided
tour.

### How big is it, honestly

Line counts are `wc -l`, so you can check them:

| | lines |
|---|---|
| the evaluator — AST, parser, safety checks, stratification, semi-naive (`datalog.py` 1–801) | 801 |
| its CLI, result printing, and `--explain` (`datalog.py` 802–1200) | 399 |
| eight satellite modules, one classical technique each | 2,092 |
| **whole toolkit, nine files** | **3,292** |

Of those 3,292 lines: 2,043 are code, 787 are commentary, 462 are
blank. `tests.py` adds a further 1,288, which is the ratio the project
is actually built on — roughly one line of test for every 2.7 lines of
toolkit, and every shipped program, exercise answer and README command
is executed by it.

"Tiny" is a claim about the evaluator, and about each module taken on
its own: none is longer than 380 lines, and every one is meant to be
read start to finish. It is not a claim that the whole repository is
small — it is nine modules because it teaches nine things.

The commentary is not overhead to be trimmed. It is roughly a quarter
of the file volume on purpose: this is a repository where the source is
assigned reading, so the explanation lives next to the code rather than
only in the lessons. There is no dead code to golf away (checked), and
shrinking it further would mean deleting either a technique or an
explanation.

## License

MIT.
