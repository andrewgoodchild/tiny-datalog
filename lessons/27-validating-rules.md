# Lesson 27 — Validating rules: which rule is wrong, and would anyone notice

> Needs lesson 17. The section on equivalent mutants needs lesson 16,
> and the one on learned rules needs lessons 25–26; both say so.

Lesson 17 found a bug by having a person read a derivation tree and
spot the step that should not be there. That worked because the tree
had three lines and the reader knew the policy. Lessons 25 and 26 then
produced rules that nobody wrote at all, with a guarantee that they
fit their examples and no other.

So two questions are still open, and they are the two halves of
validation:

- An answer is wrong. **Which rule is at fault?**
- No answer looks wrong. **How much is that worth?**

The first has a classical answer, Shapiro's algorithmic debugging
(1982). The second has one from software testing, mutation testing
(DeMillo, Lipton and Sayward, 1978), which turns out to work better on
rules than on the programs it was invented for.

## Saying what should be true

Both halves need the same input: some statement of what the rules are
*supposed* to derive. The engine cannot supply it. A program's answers
are, by definition, what the program says.

The set of facts the author had in mind is called the **intended
interpretation**, and anything that answers questions about it is an
**oracle**. `diagnose.py` builds one from four sources, which mix:

| Source | What it says |
|---|---|
| `--wrong FACT`, `--missing FACT` | one symptom, stated on the spot |
| `--expect FILE` | an expectations file: a fact must be derived, `:- fact.` must never be |
| `--against FILE` | a reference program; its answers are right, for every predicate it defines |
| `--ask` | you, answering yes or no about one fact at a time |

An expectations file is written in the language, and looks like lesson
25's examples because it is the same format:

```prolog
% programs/lending.expect
may_borrow(iris).        % a member in good standing
may_borrow(lena).        % staff, overdue, borrowing anyway
:- may_borrow(jon).      % an overdue member waits
:- may_borrow(kim).      % suspension applies to everybody
```

It has to be a separate file. Lesson 17's constraints live inside the
program, and that works for "must never hold". But a *positive*
expectation written into the program is just a fact: `may_borrow(iris).`
would make itself true, and test nothing.

## A wrong answer

Lesson 17's draft 2 let a suspended staff member borrow. Say so:

```
$ python3 diagnose.py programs/lending-draft2.dl --wrong 'may_borrow(kim)'
1 wrong answer, 0 missing

wrong: may_borrow(kim)
   may_borrow(kim) should not hold   [via may_borrow(P) :- staff(P).]
   => the rule at fault: may_borrow(P) :- staff(P).
      its body is true and its head is false at P = kim
```

That is the conclusion lesson 17 reached by eye, and the last line is
the definition of a wrong rule. A rule is a claim: whenever the body
holds, so does the head. Here is a case where the body holds
(`staff(kim)` is a stated fact) and the head does not. The claim is
false, and no other rule needs to be consulted to know it.

The algorithm is that definition applied down a derivation:

> Take the wrong fact's derivation. If one of its premises is also
> wrong, the fault lies further down: move to that premise and repeat.
> If every premise is right, this rule made a false conclusion from
> true premises. It is the culprit.

The search always ends, because a derivation is finite and each step
moves down it. It needs the oracle at every step, to say whether a
premise is right. With a three-line tree that hardly matters. Here is
a tree where it does.

`programs/access-draft.dl` is lesson 20's access policy after somebody
tidied one rule. Alice owns the roadmap document, and now, apparently,
the whole company folder. `programs/access.dl` is the version from
before the change, so use it as the oracle:

```
$ python3 diagnose.py programs/access-draft.dl --against programs/access.dl --wrong 'can(alice, delete, company)'
1 wrong answer, 0 missing

wrong: can(alice, delete, company)
   can(alice, delete, company) should not hold   [via can(U, delete, O) :- user(U), has(U, owner, O).]
     has(alice, owner, company) should not hold   [via has(U, R, F) :- parent(O, F), has(U, R, O).]
       has(alice, owner, eng_folder) should not hold   [via has(U, R, F) :- parent(O, F), has(U, R, O).]
   => the rule at fault: has(U, R, F) :- parent(O, F), has(U, R, O).
      its body is true and its head is false at F = eng_folder, O = roadmap, R = owner, U = alice
```

Read it as a chain of blame. The `can` rule is innocent: its premise
`has(alice, owner, company)` was already wrong. So was the premise
under that. The search stops at the first rule whose premises are all
right, `parent(roadmap, eng_folder)` and `has(alice, owner, roadmap)`,
and whose conclusion is not. That rule passes ownership *up* from a
document to its folder. The policy passes it down.

Compare `--explain` on the same fact. It prints the same tree, eight
lines of it, every one of them a correct description of what the
engine did. The debugger's contribution is the one thing a derivation
cannot contain: which lines are *false*.

## A missing answer

The other kind of symptom has no derivation to walk. Bob is in sales,
sales is staff, staff may view the company folder, the roadmap is
inside it, and Bob cannot view the roadmap.

For a missing fact the question is turned round:

> Look for a rule, and a substitution, whose body is true in the
> intended interpretation. If there is one, the rule is fine and
> something it needs is missing too (or, under `not`, wrongly
> present): move there and repeat. If there is none, the fact is
> **uncovered**: no rule could derive it from true facts. A rule is
> missing, or one is too strict.

```
$ python3 diagnose.py programs/access-draft.dl --against programs/access.dl --missing 'can(bob, view, roadmap)'
0 wrong answers, 1 missing

missing: can(bob, view, roadmap)
   can(bob, view, roadmap) should hold   [via can(U, view, O) :- user(U), has(U, viewer, O).]
     has(bob, viewer, roadmap) should hold, and no rule for has/3 has a true body
   => a rule for has/3 is missing, or one is too strict: nothing true implies has(bob, viewer, roadmap)
```

Again the `can` rule is cleared: its body would be true if
`has(bob, viewer, roadmap)` held, so the problem is that it does not.
And nothing true implies that fact. Bob has no grant on the roadmap,
his groups have none, and the one rule that used to carry a folder's
grants down to its documents now points the other way.

A wrong answer convicts a rule. A missing answer can only convict a
*predicate*: the fault is something that is not there, and there are
many ways to supply it. Lesson 17's why-not has the same shape for
the same reason.

The two searches call each other through negation. If a wrong answer
rests on `not q(a)`, and `q(a)` should have held, the wrong answer is
explained by a missing one, and the search changes sides.

## When the oracle does not know

A reference program is a luxury. Usually what you have is a handful of
expectations about the *outputs*, and nothing about the predicates in
between. `programs/access.expect` is eight lines about `can` and
`allowed`:

```
$ python3 diagnose.py programs/access-draft.dl --expect programs/access.expect
1 wrong answer, 1 missing

wrong: can(alice, delete, company)
   can(alice, delete, company) should not hold   [via can(U, delete, O) :- user(U), has(U, owner, O).]
   => the rule at fault: can(U, delete, O) :- user(U), has(U, owner, O).
      its body is true and its head is false at O = company, U = alice
      unless the fault is one step further down (settle it with --expect or --ask): has(alice, owner, company) is wrong

missing: can(bob, view, roadmap)
   can(bob, view, roadmap) should hold, and no rule for can/3 has a true body
   => a rule for can/3 is missing, or one is too strict: nothing true implies can(bob, view, roadmap)
      unless the fault is one step further down (settle it with --expect or --ask): has(bob, viewer, roadmap) is missing
```

The debugger does not guess. It blames the last rule it can prove
anything about, and then says exactly which unanswered question would
move the blame: is `has(alice, owner, company)` wrong as well? Nobody
told it.

Two assumptions keep those questions few. The data is taken as given:
a stated fact is true, and an unstated fact of a predicate with no
rules is false. (That is lesson 4's closed world, and lesson 4's
warning applies.) Only *derived* facts that nobody has vouched for are
in doubt.

`--ask` puts the open questions to you. Shapiro's debugger was
interactive from the start; the insight was that a programmer who
cannot say what is wrong with a program can still say whether one
fact is true. Answers are piped in here so the transcript can be
reproduced:

```
$ printf 'n\nn\ny\ny\nn\n' | python3 diagnose.py programs/access-draft.dl --expect programs/access.expect --ask
1 wrong answer, 1 missing
is has(alice, owner, company) true? [y/n] n
is has(alice, owner, eng_folder) true? [y/n] n
is has(alice, owner, roadmap) true? [y/n] y
is has(bob, viewer, roadmap) true? [y/n] y
is has(bob, editor, roadmap) true? [y/n] n

wrong: can(alice, delete, company)
   ...
   => the rule at fault: has(U, R, F) :- parent(O, F), has(U, R, O).
      its body is true and its head is false at F = eng_folder, O = roadmap, R = owner, U = alice

missing: can(bob, view, roadmap)
   ...
   => a rule for has/3 is missing, or one is too strict: nothing true implies has(bob, viewer, roadmap)
```

Five questions, each about one fact, and the same two verdicts, by
the same two chains of blame, as the reference program gave. The number of questions is the cost of the
method. This debugger asks them top-down, one per step of the chain;
Shapiro's *divide and query* asks about the middle of the tree first
and halves it each time, which matters when the tree is a
four-hundred-step recursion and the oracle is a person (exercise 3).

## Checking a change

With a reference program and no named symptom, the debugger compares
everything:

```
$ python3 diagnose.py programs/access-draft.dl --against programs/access.dl
18 wrong answers, 19 missing

wrong: allowed(alice, delete, company), allowed(alice, delete, eng_folder), allowed(alice, edit, company), and 15 more
   has(alice, editor, company) should not hold   [via has(U, R, F) :- parent(O, F), has(U, R, O).]
   => the rule at fault: has(U, R, F) :- parent(O, F), has(U, R, O).
      its body is true and its head is false at F = company, O = eng_folder, R = editor, U = alice

missing: allowed(alice, view, handbook), allowed_open(alice, view, handbook), can(alice, view, handbook), and 16 more
   has(alice, viewer, handbook) should hold, and no rule for has/3 has a true body
   => a rule for has/3 is missing, or one is too strict: nothing true implies has(alice, viewer, handbook)
```

Thirty-seven differences across four predicates, and two findings,
which are one edit seen from both sides: the new rule derives things
it should not, and the old rule's conclusions have nothing to derive
them. A diff of the two outputs would have shown the 37. This shows
the one line to change.

The exit status is 3 when anything differs, so a refactor can be
gated on it. It is a check on *these facts*, like every test. For
rules without negation or recursion, lesson 16 can do better and
prove two rules equal on every database; the two tools answer the same
question at different strengths, and the weaker one works everywhere.

## Under the hood

Open `tiny_datalog/diagnose.py`. It is mostly reuse.

`_wrong_step` calls `_derivation_of`, the function behind `--explain`
(lesson 2's *Under the hood*): one rule and its premises, each premise
derived strictly earlier. That ordering is what guarantees the walk
ends.

`_missing_step` needs to run a rule body against the *intended*
interpretation instead of the program's own answers. So the `Oracle`
keeps a second database, `world`: the program's answers, corrected by
everything known. It is an ordinary `Engine` whose relations were
filled in by hand, and `world.substitutions(rule, seed)` is the same
join that evaluates every rule in the course. Finding a covering rule
instance is evaluating the rule in a different world.

`locate` is a loop, not a recursion, for the reason `explain` is one:
a chain of blame can be as long as the longest derivation.

## Would anyone notice?

Now the second question. Suppose the debugger reports nothing:

```
$ python3 diagnose.py programs/lending-checked.dl --expect programs/lending.expect
0 wrong answers, 0 missing
the program agrees with everything stated, on these facts
```

That sentence is as strong as the expectations behind it. Four
expectations is not many. Would forty have found more? There is a way
to measure, and it is to break the rules on purpose.

A **mutant** is the program with one small edit, of a kind a tired
author makes: a rule deleted, a condition dropped from a body, a `not`
added or removed, two arguments swapped, a comparison flipped. Run the
tests against each mutant. If a test fails, the mutant is **killed**:
the tests would have noticed that mistake. If every test passes, it
**survived**, and you have found a mistake you could make tomorrow
without anything turning red.

Start with lesson 17's final program and only its three integrity
constraints as tests:

```
$ python3 mutation.py programs/lending-checked.dl
3 rules, tested by 3 constraints and 0 expectations
10 mutants: 6 killed, 4 survived, 0 equivalent   (score 60%)
(5 more edits were not legal programs: unsafe, or unstratified)
4 survived by changing an answer nothing checks.  Expecting these would kill them:
  has_overdue(jon).                         % kills 2
  may_borrow(iris).                         % kills 1
  may_borrow(lena).                         % kills 1
```

Three of the four survivors are rules deleted outright, and that is a
fact about constraints, not about this policy. A constraint says what
must never happen. A rule set that lets *nobody* borrow breaks none of
them. Constraints can only catch a program that derives too much, so a
test suite made of constraints alone is blind in one eye.

The fourth is subtler. Swap the arguments of `overdue(P, _)` and
`has_overdue` becomes a list of books; Jon is no longer on it, so Jon
borrows. The constraint that exists to stop him,
`:- may_borrow(P), has_overdue(P), not staff(P).`, says nothing,
because it reads the same broken predicate. A test written in terms of
a derived predicate inherits that predicate's mistakes.

Add the four expectations:

```
$ python3 mutation.py programs/lending-checked.dl --expect programs/lending.expect
3 rules, tested by 3 constraints and 4 expectations
10 mutants: 10 killed, 0 survived, 0 equivalent   (score 100%)
(5 more edits were not legal programs: unsafe, or unstratified)
```

The parenthesis is the engine's own contribution. Five edits produced
something lesson 3 refuses to run. Safety and stratification are
tests too, and they are free.

## Three kinds of survivor

A bigger program, tested by the eight expectations of
`programs/access.expect`:

```
$ python3 mutation.py programs/access.dl --expect programs/access.expect
12 rules, tested by 0 constraints and 8 expectations
71 mutants: 44 killed, 27 survived, 0 equivalent   (score 61%)
(26 more edits were not legal programs: unsafe, or unstratified)
25 survived by changing an answer nothing checks.  Expecting these would kill them:
  allowed(dana, view, payroll).             % kills 16
  allowed_open(alice, view, handbook).      % kills 8
  :- allowed_open(bob, view, company).      % kills 1
2 survived by changing no answer: these facts lack the case that matters
  drop-literal  can(U, delete, O) :- user(U), has(U, owner, O).
            ->  can(U, delete, O) :- has(U, owner, O).
  drop-literal  allowed(U, A, O) :- can(U, A, O), hr_feed_current, not suspended(U).
            ->  allowed(U, A, O) :- can(U, A, O), not suspended(U).
```

**Survivors that change an answer.** Twenty-five mutants derive
something different and no expectation looks. The report does not
list them (`-v` does). It lists three expectations that would kill all
25, chosen greedily: whichever kills the most, then the most of what
is left. The first is telling. Nothing in the file mentions Dana or
`payroll`, the one document with a single owner and no folder, so
sixteen mutants go unseen, most of them ways of breaking "owners
edit, editors view".

Treat that list with care. Each line is the program's *current*
answer, written down. Adding it is a regression test: it pins the
behaviour, right or wrong. Read each one and ask whether it is true
before pasting it in. That is one yes/no question about one fact,
which is the same currency the debugger dealt in.

**Survivors that change nothing here.** Two mutants derive exactly
what the original does, and they are the most interesting lines in
the report. Each drops a guard, and no expectation could ever catch
it *on these facts*, because the facts never exercise the guard:

- `user(U)` stops a group from holding permissions as if it were a
  person. No group in the data owns anything, so nothing changes when
  the check for `delete` goes.
- `hr_feed_current` is lesson 20's fail-closed switch: if the
  suspension feed did not load, allow nothing. In the data the feed is
  always current.

The fix for these is not an expectation. It is a *fact*: a test
database in which a group owns a document, and one in which the feed
is down. Lesson 17 said to run constraints on data that contains the
awkward cases. Mutation testing is how you find out which awkward
cases your data is missing.

**Survivors that change nothing anywhere** are the third kind, and
they are where Datalog does something ordinary testing cannot.

## The equivalent mutant, decided

Mutation testing has a well-known hole. Some mutants are not mistakes:
the edited program behaves identically on every input. No test can
kill one, so they drag the score down for no reason, and telling them
apart from real survivors is undecidable for a general-purpose
language. In practice somebody reads them.

For a rule without negation, "behaves identically on every database"
is lesson 16's question, and lesson 16 answered it. Two conjunctive
rules are equivalent exactly when each maps homomorphically into the
other. So `mutation.py` asks `containment.py` about every survivor,
and the ones it can prove equivalent are set aside and not scored:

```
$ python3 mutation.py programs/minimise.dl
4 rules, tested by 0 constraints and 0 expectations
30 mutants: 0 killed, 28 survived, 2 equivalent   (score 0%)
...
2 equivalent on every database, by containment, so not counted:
  drop-literal  has_edge(X, Y) :- edge(X, Y), edge(X, Z).
            ->  has_edge(X, Y) :- edge(X, Y).
  drop-literal  two_hop(X) :- edge(X, Y), edge(Y, Z), edge(X, W).
            ->  two_hop(X) :- edge(X, Y), edge(Y, Z).
```

Those are lesson 16's two redundant atoms, found from the other
direction: a condition you can drop without any possible test
noticing was never a condition. (A dropped *rule* is checked the same
way: it is redundant if another rule for the same head contains it.)

The proof is rule against rule, which is enough even in a recursive
program: two rules that agree on every database agree on whatever the
rest of the program feeds them. Where a rule has `not`, a comparison
or an aggregate, the theory stops, as it did in lesson 16, and the
mutant is reported as a survivor for a person to judge.

## Rules nobody wrote

Lesson 26 learned two rules for `ancestor` from twelve examples.
`programs/ancestor-learned.dl` is those rules with the facts they
were learned over. They fit their examples by construction, so
`diagnose.py` has nothing to say about them. Mutation testing does:

```
$ python3 mutation.py programs/ancestor-learned.dl --expect programs/ancestor-sparse.examples
2 rules, tested by 0 constraints and 12 expectations
7 mutants: 7 killed, 0 survived, 0 equivalent   (score 100%)
(5 more edits were not legal programs: unsafe, or unstratified)
```

For a learned rule the score means something slightly different, and
more useful. A surviving mutant would be *another rule set that fits
the same examples*: evidence that the examples did not determine the
answer, and that the learner's choice between them was arbitrary. No
survivors says the twelve examples pin these two rules down, at least
against their one-edit neighbours.

And since this family tree is small enough to know completely, the
learned rules can be held against examples they never saw:

```
$ python3 diagnose.py programs/ancestor-learned.dl --expect programs/ancestor.examples
0 wrong answers, 0 missing
the program agrees with everything stated, on these facts
```

All 17 pairs, from rules learned on 6 of them. Held-out examples are
the first test to run on anything learned, by FOIL, by a solver or by
a language model.

They are not the last. Lesson 25's FOIL was given the same twelve
examples and learned three rules with no recursion, one of which says
that anyone with a great-grandchild is the ancestor of anyone with a
parent. `programs/ancestor-foil.dl` is those rules. Run the same two
checks:

```
$ python3 mutation.py programs/ancestor-foil.dl --expect programs/ancestor-sparse.examples
3 rules, tested by 0 constraints and 12 expectations
16 mutants: 16 killed, 0 survived, 0 equivalent   (score 100%)
(10 more edits were not legal programs: unsafe, or unstratified)
```

```
$ python3 diagnose.py programs/ancestor-foil.dl --expect programs/ancestor.examples
0 wrong answers, 0 missing
the program agrees with everything stated, on these facts
```

A perfect score, and all 17 held-out pairs. Every tool in this lesson
passes both rule sets, and they are not the same rules. One stranger
tells them apart:

```
$ python3 datalog.py --assume 'parent(zed, yan).' -q 'ancestor(ada, yan)' programs/ancestor-foil.dl
?- ancestor(ada, yan)
   ancestor(ada, yan).
   (1 answer)
```

```
$ python3 datalog.py --assume 'parent(zed, yan).' -q 'ancestor(ada, yan)' programs/ancestor-learned.dl
?- ancestor(ada, yan)
   (0 answers)
```

The examples, the held-out examples and the mutants were all drawn
from one family, and on that family the two programs agree. Tests
check a program on the data they were written against. Whether the
rules are right on data of a *different shape* is a question about
the rules, and the only instrument for it so far is to read them:
three lines of Datalog, one of which is plainly not what "ancestor"
means. That is the argument the README opened with. A learned
artefact you can read is one you can refuse.

## The course, checked by its own lesson

Every program in `programs/` that the engine will run has an
expectations file beside it: `programs/tweety.dl` has
`programs/tweety.expect`, and so on for thirty more. A test in
`tests.py` holds three things. Each program derives what its file
says. Each buggy draft (`access-draft.dl`, `lending-draft2.dl`,
`lending-typo.dl`) is caught by the file for the finished version.
And no mutant that changes an answer survives, with one exception
kept on purpose: `access.dl`, whose gaps this lesson teaches from. A
program with no file must be on a short list that says why, such as
"refused by the engine, which is the point of its lesson".

Writing them was the lesson again in small. `programs/family.expect`
cannot say `:- sibling(X, X).` because lesson 1's sibling rule is
wrong on purpose, and an expectation that is true would fail. The
suggested list for that program offered `sibling(ann, ann).` instead,
which kills three mutants and is false: the warning above about
pasting, met in practice. And the scores vary for the reason given
under "survivors that change nothing here":

```sh
$ python3 mutation.py programs/token.dl --expect programs/token.expect
5 rules, tested by 0 constraints and 5 expectations
19 mutants: 10 killed, 9 survived, 0 equivalent   (score 52%)
(3 more edits were not legal programs: unsafe, or unstratified)
9 survived by changing no answer: these facts lack the case that matters
   ...
```

Lesson 20's token is checked against one request, a write to
`file1`, which is refused. Nine edits to the rules refuse that
request too. No expectation can do better; a second request can. The
programs that score 100% are mostly small recursions over a graph
with a direction, where every edit shows.

## What none of this checks

**A score is about the tests, not the rules.** 100% means every
one-edit mistake in this list would be noticed. It does not mean the
rules are right, and it says nothing about mistakes two edits away or
of a kind not on the list.

**The oracle is a person, or was written by one.** Every verdict
above traces back to someone saying "this fact should hold". The
debugger makes that the *only* thing they have to say, one fact at a
time, and lesson 17's division of labour stands: the engine checks
that the rules agree with each other and with what you told it, and
only you can say what you meant.

**"On these facts."** Diagnosis, expectations and all but one kind of
mutant verdict are statements about the data in front of them. The
exception is the equivalent mutant, and it is an exception for the
reason the course keeps returning to: the language was kept small
enough for the question to have an answer.

## Exercises

1. Draft 2 of the lending policy passes `--wrong 'may_borrow(kim)'`
   to one rule. Run `diagnose.py` on `programs/lending-draft2.dl` with
   `--expect programs/lending.expect` instead. Is the verdict the
   same? Why does the oracle need nothing beyond the file this time?
2. In `programs/access-draft.dl`, the wrong rule is found from
   `can(alice, delete, company)` after descending two levels. Predict
   the chain of blame for `--wrong 'allowed(alice, delete, company)'`
   (still `--against programs/access.dl`) before running it. Which
   extra rule appears in the chain, and why is it not blamed? Then try
   `--wrong 'can(alice, view, company)'` and explain the refusal.
3. A chain of blame through a 400-step recursion costs up to 400
   questions asked top-down. Describe the order *divide and query*
   would ask them in, and how many it needs. Why is it sound to
   discard everything below a fact the oracle calls right, and
   everything above one it calls wrong?
4. `mutation.py programs/access.dl --expect programs/access.expect`
   reports two survivors that change no answer. Use `--assume` (lesson
   24) with `datalog.py` to find a single added or removed fact under
   which each mutant and the original would differ, and say what
   expectation you would then write.
5. Add `X != Y` to the body of `sibling` in a copy of
   `programs/family.dl` and mutation-test it with no expectations.
   One mutant flips the comparison. Why is it not reported as
   equivalent, whatever it does, and which lesson's boundary is that?
6. Lesson 26's rules for same-generation were
   `sg(X, X) :- parent(X, Y).` and
   `sg(X, Y) :- parent(P, X), parent(Q, Y), sg(P, Q).` They reproduce
   all 23 examples. Now a second family moves in: add
   `parent(zed, yan).` Is Yan in the same generation as Ben? What do
   the learned rules say, and which of this lesson's tools would have
   warned you?

Back to [the index](getting-started.md).
