# Lesson 20 — answers

Runnable rules: `exercises/20-answers.dl`.

**1. Separation of duties.**

```prolog
violation(R) :- requested(R, U), approved(R, U).
```

`r2` (Carol approved her own) and `r3` (Dan approved his own, even
though Erin also approved it) are violations; `r1` is not. No `!=` is
needed because the rule asks for *equality*, and a repeated variable
already is an equality test: the join on `U` only succeeds when the
requester and the approver are the same constant. You would need `!=`
for the opposite rule, "approved by someone *other* than the
requester", and lesson 14 explains why that built-in is harmless when
both sides are bound. The violation form is the better one for an
audit anyway: it names the offending request, while a "properly
approved" relation leaves the reader to notice what is missing from
it.

**2. A ban that overrides a group grant.**

```prolog
allowed_b_open(U, A, O) :- can(U, A, O), not banned(U, O).               % fails open
allowed_b(U, A, O)      :- can(U, A, O), bans_loaded, not banned(U, O).  % fails closed
```

With the bans loaded, both rules agree. Remove `bans_loaded.` and the
`banned` facts together (the feed failed) and `--explain` on a banned
user shows the difference a reviewer needs to see. For
`allowed_b_open`, the tree ends in `not banned(...)   (absent from its
completed stratum)`, which is a grant justified by an empty table. For
`allowed_b`, the why-not output reports `blocked at: bans_loaded -- no
matching fact`, which names the missing authority. The second tree is
the one a security reviewer can act on.

**3. Forging a right, and stopping it.**

Drop the holder's check from `programs/token.dl`, append
`right(file2, write).`, and request a write to `file2`. The flattened
program authorizes it: `allow` joins `right(R, Op)` against every
`right` fact in the program, whoever wrote it. The issuer never granted
anything on `file2`, so the holder has escalated their own authority.
In one fact space, appending a *fact* is not monotone in the safe
direction: it adds a way for `allow` to succeed.

The fix is in `exercises/20-answers.dl`. Every fact carries the block
that asserted it, and the authorizer's `allow` reads `right(0, R, Op)`
only. The forged `right(2, file2, write)` is still in the program but
is invisible to the rule that matters, and `authorized` has no
answers. That is what Biscuit's scoping does natively: by default,
rules see the authority block's facts and their own block's facts, so
a later block can add checks (which only restrict) but cannot add
authority. The design lesson generalises: **monotonicity protects you
only if the untrusted party can add constraints, not premises.**

**4. Checks against lists, as the graph grows.**

| Query | facts derived, as shipped | with ten more groups under `staff` | full evaluation |
|---|---|---|---|
| `can(alice, edit, roadmap)` | 13 | 13 | 74 → 304 |
| `can(U, edit, roadmap)` | 37 | 117 | 74 → 304 |
| `can(U, view, roadmap)` | 71 | 551 | 74 → 304 |

The check does not grow at all. Its demand is seeded with alice and
the roadmap, and the new groups are neither alice's groups nor the
roadmap's folders. The list queries grow with the graph, because "who
can edit?" binds only the object, so demand flows through every group
that could reach it. The `view` list is worse than full evaluation
(551 against 304): `staff` can view the whole company, so demand
reaches every new group, and magic sets pays its guard overhead on top
of computing everything anyway. That is lesson 7's rule, in its bad
case. It is also why production systems keep check and list as
separate APIs with separate indexes. The logic is symmetric, but the
cost is not.

**5. Nesting at most two deep, without recursion.**

```prolog
in_group2(U, G) :- member(U, G).
in_group2(U, G) :- member(U, H), member(H, G).
```

You had to know the **maximum depth of the data**, and you had to know
it when you wrote the rule. The recursive rule needed no such fact: it
is correct for any depth anybody ever creates. The non-recursive
version is silently wrong the day someone nests a third level, giving
no error, just a missing permission. That is the price Cedar pays
deliberately (it puts hierarchy membership in a built-in operator over
data the application supplies, rather than in user rules), and what
it buys is a language whose policies a solver can analyse completely.
Lesson 14 made the same trade from the other side.
