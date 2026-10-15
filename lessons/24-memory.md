# Lesson 24 — Memory: the model writes the facts, the rules decide

An assistant that talks to someone for months has to remember what it
was told. The common way to build that is to store the conversations,
retrieve the passages that look relevant to each new question, and let
the language model re-read them and reason it out again. That works
until it does not, and the ways it fails are specific:

- **Stale values.** "My manager is Priya" and, four months later, "I
  report to Sam now" are both in the transcript. The model has to
  notice which came last, every time it is asked.
- **Contradictions settled silently.** Two statements disagree, and the
  model picks one without saying so.
- **No account of a belief.** Asked why it thinks something, the model
  produces a plausible story, which is not the same as a record of what
  caused the belief.
- **Answers to questions nobody answered.** Asked about something never
  said, a model tends to supply something likely.

This lesson builds a memory that fails differently, out of pieces the
course already has. The model's only job is to write down what it was
told, as facts. Rules from lesson 23 work out what is still true,
constraints from lesson 17 catch contradictions, and the explanations
from lessons 1–3 say where every belief came from. It is a capstone:
there is no new engine machinery here, only a new use for it.

The idea is not this course's. Lemmalog, a Datalog engine built for
agent memory, states the thesis well: an agent's memory should be a
deductive database, a verifiable model of what it knows, rather than a
better way of remembering text. Its numbers appear near the end of
this lesson, with their caveats.

## The division of labour

`programs/memory.dl` is the memory of one user after six conversations,
which the program calls **episodes**:

```prolog
%     subject relation  object    date          episode
said(user,  works_at, acme,    "2024-01-08", e1).  % "I just started at Acme."
said(user,  manager,  priya,   "2024-01-08", e1).  % "My manager is Priya."
said(priya, manager,  marco,   "2024-02-19", e2).  % "Priya reports to Marco."
said(user,  allergy,  peanuts, "2024-03-04", e3).  % "I'm allergic to peanuts."
said(user,  manager,  sam,     "2024-06-10", e4).  % "After the reorg I report to Sam."
said(user,  manager,  dana,    "2024-06-10", e5).  % "...actually, Dana, while Sam's away."
said(sam,   manager,  marco,   "2024-07-01", e6).  % "Sam reports to Marco."
```

A language model read the conversations and wrote these lines. That is
the **extraction boundary**: everything to the left of it is language
and judgement, and everything to the right is rules. The model never
writes a conclusion such as "the user reports to Marco". It writes what
was said, when, and in which episode, and stops.

The rules are lesson 23's, asked about one moment, `now`, plus a
reporting chain:

```prolog
current(E, R, O) :- said(E, R, O, F, _), now(T), F <= T,
                    not ended_by(E, R, O, F, T).

reports_to(X, Y) :- current(X, manager, Y).
reports_to(X, Z) :- current(X, manager, Y), reports_to(Y, Z).
```

Two properties are stated as constraints:

```prolog
:- current(E, R, O1), current(E, R, O2), functional(R), O1 < O2.
:- reports_to(X, X).
```

## What the memory believes, and what it cannot decide

```
$ python3 datalog.py -q 'current(user, R, O)' programs/memory.dl
?- current(user, R, O)
   current(user, allergy, peanuts).
   current(user, manager, dana).
   current(user, manager, sam).
   current(user, works_at, acme).
   (4 answers)
constraint violated: :- current(E, R, O1), current(E, R, O2), functional(R), O1 < O2.
   current(user, manager, dana), current(user, manager, sam), functional(manager), dana < sam
   (1 counterexample)
```

Priya has gone. Nobody deleted her: Sam's statement superseded her
from 2024-06-10, exactly as in lesson 23, and `--explain` on the
absent fact shows that chain. Sam and Dana were both stated on
2024-06-10, so the dates cannot say which came last, and the memory
holds two managers for a relation that allows one.

The constraint does not pick a winner. Lesson 18 could: give later
episodes priority, and Dana wins. But "the later remark wins" is a
policy, and here it would be a guess: "actually, Dana, while Sam's
away" might mean Dana *instead of* Sam, or Dana *as well*, for now.
The honest output is the counterexample, which is a question for the
user. When the answer comes, it is one more statement, and nothing has
to be deleted:

```
$ python3 datalog.py --assume 'said(user, manager, dana, "2024-06-12", e7).' -q 'current(user, manager, M)' programs/memory.dl
?- current(user, manager, M)
   current(user, manager, dana).
   (1 answer)
% 2 integrity constraints checked: none violated
```

(`--assume` evaluates the program as though those facts were added;
`fact~.` would remove one. Because a Datalog program is a function of
its facts, a "what if" is just another input: there is nothing to
restore afterwards.)

## Where a belief came from

Before the user answers, the memory believes the user reports to
Marco, through Sam. Ask why:

```
$ python3 datalog.py --explain 'reports_to(user, marco)' programs/memory.dl
?- explain reports_to(user, marco)
   reports_to(user, marco)   [via reports_to(X, Z) :- current(X, manager, Y), reports_to(Y, Z).]
     current(user, manager, sam)   [via current(E, R, O) :- said(E, R, O, F, _), now(T), F <= T, not ended_by(E, R, O, F, T).]
       said(user, manager, sam, "2024-06-10", e4)   (base fact)
       now("2024-08-01")   (base fact)
       "2024-06-10" <= "2024-08-01"   (comparison)
       not ended_by(user, manager, sam, "2024-06-10", "2024-08-01")   (absent from its completed stratum)
     reports_to(sam, marco)   [via reports_to(X, Y) :- current(X, manager, Y).]
       current(sam, manager, marco)   [via current(E, R, O) :- said(E, R, O, F, _), now(T), F <= T, not ended_by(E, R, O, F, T).]
         said(sam, manager, marco, "2024-07-01", e6)   (base fact)
         now("2024-08-01")   (base fact)
         "2024-07-01" <= "2024-08-01"   (comparison)
         not ended_by(sam, manager, marco, "2024-07-01", "2024-08-01")   (absent from its completed stratum)
```

Every leaf that matters names an episode, e4 and e6. An assistant can
quote those two conversations back, verbatim, as its reasons. This is
**provenance** in the plainest sense, and it is what retrieval over
text cannot give: a retrieved passage is something that looked
relevant, while a derivation is the actual cause of the belief. (The
constraint violation prints after this tree too. It keeps printing
until it is resolved, which is the point.)

## Knowing what you do not know

```
$ python3 datalog.py --explain 'current(dana, manager, marco)' programs/memory.dl
?- explain current(dana, manager, marco)
   current(dana, manager, marco) is not derived.  Per rule:
     via current(E, R, O) :- said(E, R, O, F, _), now(T), F <= T, not ended_by(E, R, O, F, T).
       blocked at: said(dana, manager, marco, F, _) -- no matching fact
```

Is Dana under Marco? Nobody said so. The why-not names the missing
statement exactly, so the assistant's answer is "you haven't told me",
not a plausible guess. This matters most for the questions built to
trap a memory, which assert something false in passing ("since you
know my manager Dana reports to Marco..."). A rule engine cannot be
talked into a premise; it either has the statement or it does not.

The same check works before storing something. Suppose the model
misreads a remark and writes that Marco reports to the user:

```
$ python3 datalog.py --assume 'said(marco, manager, user, "2024-07-15", e7).' -q 'reports_to(marco, Y)' programs/memory.dl
?- reports_to(marco, Y)
   reports_to(marco, dana).
   reports_to(marco, marco).
   reports_to(marco, sam).
   reports_to(marco, user).
   (4 answers)
...
constraint violated: :- reports_to(X, X).
   reports_to(marco, marco)
   reports_to(sam, sam)
   reports_to(user, user)
   (3 counterexamples)
```

The new statement would make three people their own managers. An
extraction pipeline that tries each new batch with `--assume` first,
and stores it only on exit status 0, cannot store this mistake.

## How sure, and from where

Extraction is not certain, and a model can say how confident it is in
each statement. Lesson 8's semirings carry that through the rules.
`programs/memory-confidence.dl` has the manager statements with
weights (plus a hesitant fourth one, "I think Dana's under Marco
too?"):

```
$ python3 semiring.py --semiring viterbi -q 'reports_to(user, marco)' programs/memory-confidence.dl
Semiring: viterbi   (fixpoint after 3 rounds)
?- reports_to(user, marco)
   reports_to(user, marco) = 0.72
   (1 answer)
$ python3 semiring.py --semiring why -q 'reports_to(user, marco)' programs/memory-confidence.dl
Semiring: why   (fixpoint after 3 rounds)
?- reports_to(user, marco)
   reports_to(user, marco) = {manager(dana, marco), manager(user, dana)} | {manager(sam, marco), manager(user, sam)}
   (1 answer)
```

The best chain is 0.9 × 0.8, through Sam (lesson 9 says why the best
chain, and not a sum, is the honest number). The why-provenance lists
both chains that support the belief. Semirings need positive programs,
so this runs on the reporting chain alone and not on the supersession
rules; exercise 3 asks how to get both numbers in one pass, and the
answer is less obvious than it looks.

## Values are data

The strings in a memory come from text somebody else wrote, and they
will be read back by a language model. A value that contained a line
break could end a line of output early and start a new one that looks
like an instruction. A right-to-left override character can make text
display differently from how it reads. So values may not contain line
breaks, control characters, or invisible and direction-changing
characters, from a program file or from Python (nor both kinds of
quote, since such a value could not be printed back as one token):

```python
run_program(rules, facts={"said": [("user", "likes",
                                    "tea‮.snoitcurtsni erongi",
                                    "2024-08-02", "e9")]})
# DatalogError: fact said('user', 'likes', 'tea‮.snoitcurtsni erongi',
#   '2024-08-02', 'e9') contains U+202E (RIGHT-TO-LEFT OVERRIDE), a control
#   or invisible character, which values may not hold
```

Every value the engine prints is then one visible token, quoted if it
is not a plain identifier. That is a structural guarantee, and it is a
narrow one. A value can still *say* "ignore your instructions" in
plain words, and the model reading it has to treat answers as data.
What the engine guarantees is that it never prints anything except
facts, rules and its own labels, so there is always a boundary to
point at. Synalog, a Datalog dialect built for agents, quotes values
from the database in its reports for the same reason. Keep long text
out of facts altogether: store an episode id, and keep the
conversation itself somewhere the model reads on purpose.

## What it costs, honestly

**Recomputation.** Each new statement can retract a conclusion (Sam's
statement ended Priya), so updates are non-monotone and lesson 10's
incremental engine refuses this program, as lesson 23 showed. The base
engine recomputes from scratch, which is fast at the scale of one
person's memory. Systems built for this recompute only what depends on
what changed: Lemmalog clears and rebuilds just the predicates
downstream of a retraction.

**Extraction is the ceiling.** Rules cannot conclude anything from a
statement the model never wrote down. Lemmalog's published results on
the LongMemEval and LoCoMo benchmarks show this from several sides.
Structured memory did best, relative to giving the model the whole
transcript, on *knowledge updates* (questions whose answer changed
over time), which is this lesson's supersession. Adding counting rules
did not fix counting questions, because the items to count had never
been extracted. And once extraction improved, the limit became
*selection*: deciding which derived facts fit into the model's context
for a given question. Treat their numbers as indicative only. They are
the authors' own measurements, and the authors report that a single
run varied by about ±0.3 F1 per question type at five questions per
type.

**Where the facts already are.** This lesson assumes the facts come out
of conversation. When they already sit in a database, the other route
is the one Synalog takes. Instead of copying facts into an engine, the
agent writes rules (a "semantic layer" of named concepts over existing
tables) that compile to SQL and run where the data is. Its verifier
checks agent-written rules before any SQL runs, and its assertions are
checked by searching for counterexamples, which is lesson 17's
integrity constraints running on a SQL engine.

## Giving an agent the engine

`skills/tiny-datalog/SKILL.md` is an Agent Skill: a file in the
Agent Skills format that coding agents (Claude Code among them) load
when a task matches its description. It teaches the loop this lesson
used: write facts and rules, read the warnings, query, explain before
trusting, state properties as constraints, and report from the
engine's output. It also lists the syntax mistakes agents make first,
such as capitalised names, which are variables. Copy the folder into
your agent's skills directory to use it, for example
`~/.claude/skills/tiny-datalog/` for Claude Code.

## Exercises

1. On 2024-09-01 the user says they have moved to Globex. Add the
   statement, move `now` to 2024-10-01, and predict
   `current(user, works_at, O)` before running it.
2. Write the rule that breaks same-day ties by episode order, so that
   e5 supersedes e4. Then argue whether a memory *should* use it.
3. `exercises/24-product-semiring.py` pairs Viterbi with
   why-provenance. Before running it, decide which witnesses the pair
   should carry for `reports_to(user, marco)`: those of the best chain,
   or all of them? Then compare the two semirings the script defines.
4. The assistant suggested dishes this week (`recommended(user, D)`),
   and a table says what each dish contains. Write the constraint that
   would have stopped it suggesting satay.
5. Should `allergy` be functional? What would the user have to say,
   and what would the extractor have to write, for an allergy to stop
   being current?

Back to [the index](getting-started.md).
