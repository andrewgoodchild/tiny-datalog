# Lesson 15 — answers

**1. Adding `employment_checked(dana).`**

`eligible(dana)` becomes true and `pending(dana)` disappears;
`eligible_naive` is unchanged, because it never distinguished her from
Bob in the first place. The three possible states are now recorded
properly: checked-and-employed (cyril, not eligible),
checked-and-not-employed (bob and dana, eligible), and unchecked
(nobody). The naive rule only ever had two states, which is precisely
the bug.

**2. `pending` uses `not employment_checked(P)` — is that safe?**

It is closed-world reasoning one level up: it assumes the *checking
register* is complete, i.e. that if a check had happened it would be
recorded. That is a much better bet than assuming the employment table
is complete, because the register is maintained by the process making
the decisions — it is genuinely the authority on its own activity.

The same objection still applies one level further up, and this is the
honest part: if checks can happen without being recorded, you need
`check_attempted` as well, and so on. The regress stops where some
system really is authoritative about its own contents. Finding that
level is the modelling work; assuming you are already at it is the bug.

**3. Adding one fact that removes two conclusions and adds a third.**

Chain a default off another default:

```prolog
bird(tweety).
abnormal(X) :- penguin(X).
flies(X) :- bird(X), not abnormal(X).
migrates(X) :- flies(X), not flightless_range(X).
grounded(X) :- bird(X), not flies(X).
```

With no `penguin` fact: `flies(tweety)` and `migrates(tweety)` hold,
`grounded(tweety)` does not. Add `penguin(tweety).` and both
conclusions vanish while `grounded(tweety)` appears — one fact, two
retractions, one addition. Every real default hierarchy behaves this
way, which is why non-monotone systems are hard to test: the effect of
a fact is not local to the rule that mentions it.

**4. Is well-founded *undefined* the same as open-world *unknown*?**

**Not the same.** They coincide in feeling and differ in origin.

- Well-founded *undefined* arises from **circularity**: the program
  cannot settle the atom because its truth depends on itself
  (Lesson 5's paradox). Add more facts and it may resolve. It is a
  statement about *this program's* self-reference.
- Open-world *unknown* arises from **incompleteness**: the world may
  well contain the fact, we simply were not told. Nothing about the
  axioms is circular. It is a statement about the *limits of what was
  said*.

One is "these rules cannot decide"; the other is "nobody told me".

`pending` is closer to the open-world reading — it exists precisely to
mark "we have not been told" — but it achieves that *inside* a
closed-world engine by making the absence into a positive fact about
the checking process. That is the general technique: closed-world
engines can represent open-world ignorance, but only if you model the
ignorance explicitly rather than leaving it as a gap in a table.
