# Lesson 20 — Authorization: who may do what, and the proof

Every system with a login has a rule set, whether or not anyone calls
it one. *Members of a group can see the group's folders. Folders pass
their permissions down to what is inside them. Owners can edit.
Suspended accounts can do nothing.* Each request is a question put to
those rules, and every "yes" ought to come with a reason someone can
check. That is a description of Datalog, and the field noticed long
before this course did: the logic-based security languages of the
2000s (Binder, SecPAL, the RT family) were Datalog with signatures
attached. Today a Hacker News thread can ask, in so many words,
whether Datalog is a good language for authorization, and get a
long argument in reply.

This lesson's answer: yes, for the part of authorization that is
reachability, which is most of it, provided you avoid two traps the
course has already named. Lessons 1–4 and 17 are the prerequisites;
lesson 7 helps with one section.

## The model: relationships, not roles

Role-based access control (RBAC) is the version everybody starts with:
users have roles, roles have permissions, and it is two joins. The
version that large systems converged on is **relationship-based**
(ReBAC), described in Google's **Zanzibar** paper (Pang and colleagues,
2019). Access is a graph: a user is a member of a group, the group is
a viewer of a folder, the folder contains a document. Zanzibar stores
the graph as tuples `(object, relation, subject)` and evaluates a
small rule language over them. Its open-source descendants (SpiceDB,
OpenFGA and others) keep the shape.

Strip off the service and what is left is a Datalog program.
`programs/access.dl` holds a company's folders, groups and grants, and
the policy is five rules (`has` is the relation of a subject to an
object; groups nest, so membership is recursive):

```prolog
in_group(U, G) :- member(U, G).
in_group(U, G) :- member(H, G), in_group(U, H).      % groups nest

has(U, R, O) :- grant(O, R, U).                      % granted directly
has(U, R, O) :- grant(O, R, G), in_group(U, G).      % granted to a group
has(U, R, O) :- parent(O, F), has(U, R, F).          % inherited from a folder
has(U, editor, O) :- has(U, owner, O).               % owners edit
has(U, viewer, O) :- has(U, editor, O).              % editors view

can(U, view, O)   :- user(U), has(U, viewer, O).     % people, not groups
```

Each rule is one sentence of the policy, and they compose: a grant on
`company` reaches `roadmap` through two folders and two levels of
group, and nobody had to write that path down.

```
$ python3 datalog.py -q 'can(U, view, roadmap)' programs/access.dl
?- can(U, view, roadmap)
   can(alice, view, roadmap).
   can(bob, view, roadmap).
   (2 answers)
```

Alice owns the roadmap. Bob is in sales, and nothing about sales
mentions the roadmap. Why can he see it?

## The proof is the audit log

```
$ python3 datalog.py --explain 'can(bob, view, roadmap)' programs/access.dl
?- explain can(bob, view, roadmap)
   can(bob, view, roadmap)   [via can(U, view, O) :- user(U), has(U, viewer, O).]
     user(bob)   (base fact)
     has(bob, viewer, roadmap)   [via has(U, R, O) :- parent(O, F), has(U, R, F).]
       parent(roadmap, eng_folder)   (base fact)
       has(bob, viewer, eng_folder)   [via has(U, R, O) :- parent(O, F), has(U, R, F).]
         parent(eng_folder, company)   (base fact)
         has(bob, viewer, company)   [via has(U, R, O) :- grant(O, R, G), in_group(U, G).]
           grant(company, viewer, staff)   (base fact)
           in_group(bob, staff)   [via in_group(U, G) :- member(H, G), in_group(U, H).]
             member(sales, staff)   (base fact)
             in_group(bob, sales)   [via in_group(U, G) :- member(U, G).]
               member(bob, sales)   (base fact)
```

Read it from the bottom. Bob is in sales, sales is part of staff,
staff can view the whole company, and the roadmap sits two folders
inside the company. If that is not what the business intended, the
tree also says where to cut: remove `grant(company, viewer, staff)`
and every staff member loses the roadmap, or move the roadmap out from
under `company` and only the roadmap changes. Zanzibar has an API for
exactly this tree (it calls it *Expand*), because "why does this
person have access?" is the question every security review asks
first.

The denial explains itself too. Carol is a contractor:

```
$ python3 datalog.py --explain 'can(carol, view, roadmap)' programs/access.dl
?- explain can(carol, view, roadmap)
   can(carol, view, roadmap) is not derived.  Per rule:
     via can(U, view, O) :- user(U), has(U, viewer, O).
       blocked at: has(carol, viewer, roadmap) -- no matching fact
     (2 rules for can cannot match this head and were skipped)
```

Note what the engine did *not* need: a deny rule. Nothing derived
means no access. This is lesson 4's closed-world assumption working
in your favour, because the grants table *is* the authority on who was
granted what. **Default deny comes free** in a closed world. That
matters, because the systems that get this wrong usually get it wrong
by evaluating deny rules over an allow-by-default base.

## One rule set, three questions

Authorization services are asked three kinds of question, and in most
of them each kind is a different API:

| Question | Query | Shape |
|---|---|---|
| May bob view the roadmap? (*check*) | `can(bob, view, roadmap)` | both bound |
| Who can view the roadmap? (*list subjects*) | `can(U, view, roadmap)` | object bound |
| What can bob touch? (*list objects*) | `can(bob, A, O)` | subject bound |

In Datalog they are the same rules with different arguments bound:

```
$ python3 datalog.py -q 'can(bob, A, O)' programs/access.dl
?- can(bob, A, O)
   can(bob, view, company).
   can(bob, view, eng_folder).
   can(bob, view, handbook).
   can(bob, view, roadmap).
   (4 answers)
```

The cost is not the same, though, and lesson 7 says why. A check has
two arguments bound, so magic sets can confine the work to bob's
groups and the roadmap's folders:

```
$ python3 datalog.py --magic --trace -q 'can(bob, view, roadmap)' programs/access.dl
...
[magic] 20 IDB facts derived vs 74 under full evaluation
```

"Who can view the roadmap?" binds only the object, demand spreads
through every group, and magic sets saves almost nothing (71 facts
against 74). The production systems meet the same asymmetry and solve
it with machinery: the Zanzibar paper describes a separate indexing
service, Leopard, that keeps nested group membership flattened so
checks stay fast, and the open-source descendants ship "list" endpoints
beside "check" with different performance promises. Same rules, same
answers, very different bills. The logic does not care which way you
ask, but the engine does.

## The type trap

The `user(U)` guard in `can` was not there in the first draft. Ask
the relation underneath it:

```
$ python3 datalog.py -q 'has(U, viewer, roadmap)' programs/access.dl
?- has(U, viewer, roadmap)
   has(alice, viewer, roadmap).
   has(bob, viewer, roadmap).
   has(eng, viewer, roadmap).
   has(sales, viewer, roadmap).
   has(staff, viewer, roadmap).
   (5 answers)
```

Groups are subjects in `grant`, so they turn up as viewers. That is
correct for `has` (the eng *group* does hold viewer on the roadmap),
and wrong for anything that answers "which people?". This is lesson
17's warning about types arriving in a security setting: this engine
has no types, so a principal and a group are both just constants, and
mixing them up gives a quietly wrong result, not an error. Zanzibar's
descendants added schemas with typed relations for exactly this
reason. Here, the guard does the type system's job, and it belongs in
the rule that faces the outside world.

## Revocation, and which way it fails

Now the trap from lesson 4, pointed at security. Bob has been
suspended, and the suspension list arrives from an HR feed:

```prolog
suspended(bob).                                      % from the HR feed
hr_feed_current.                                     % ...which loaded today

allowed_open(U, A, O) :- can(U, A, O), not suspended(U).          % fails open
allowed(U, A, O)      :- can(U, A, O), hr_feed_current,
                         not suspended(U).                        % fails closed
```

On a good day the two rules agree. Now suppose the feed failed to
load overnight, so both of its facts are missing:

```
$ grep -v -e '^suspended' -e '^hr_feed_current' programs/access.dl > /tmp/a.dl
$ python3 datalog.py -q 'allowed_open(U, view, handbook)' -q 'allowed(U, view, handbook)' /tmp/a.dl
?- allowed_open(U, view, handbook)
   allowed_open(alice, view, handbook).
   allowed_open(bob, view, handbook).
   allowed_open(carol, view, handbook).
   (3 answers)
?- allowed(U, view, handbook)
   (0 answers)
```

`allowed_open` gave a suspended account its access back, with an
immaculate derivation, because "not suspended" read an empty list as
a clean bill of health. `allowed` refused everybody, which is
inconvenient and safe. Every `not` in a rule that *grants* access is a
grant conditioned on absence, so it asks lesson 4's question: whose
authority says this is absent, and what if that authority is down?
The fix is lesson 4's fix: model the check (`hr_feed_current`), not
just its result. Security people call the two behaviours **fail open**
and **fail closed**, and Datalog lets you see which one you wrote by
reading the rule.

## Capabilities, and why attenuation is monotonicity

Zanzibar keeps the rules and the grants in one central service. The
other design hands the user a **capability**: a token that carries
its own permissions. **Biscuit** (from Clever Cloud) is a token format
whose contents *are* Datalog. The issuer signs a first block of facts,
and anyone holding the token can append blocks of **checks**
restricting it further before passing it on, without contacting the
issuer. That offline restriction is called **attenuation**.

`programs/token.dl` flattens one token into a plain program. The
issuer granted read and write on `file1`. The holder appended one
check, "only reads from here on", and handed the token to a service,
which then receives a write request:

```prolog
right(file1, read).                 % block 0, signed by the issuer
right(file1, write).
check(only_reads).                  % block 1, appended by the holder
passes(only_reads) :- operation(read).

resource(file1).  operation(write). % the request, at the service
allow :- resource(R), operation(Op), right(R, Op).
failed(C) :- check(C), not passes(C).
some_check_failed :- failed(_).
authorized :- allow, not some_check_failed.
```

```
$ python3 datalog.py --explain 'authorized' programs/token.dl
?- explain authorized
   authorized is not derived.  Per rule:
     via authorized :- allow, not some_check_failed.
       blocked at: not some_check_failed -- some_check_failed holds:
         some_check_failed   [via some_check_failed :- failed(_).]
           failed(only_reads)   [via failed(C) :- check(C), not passes(C).]
             check(only_reads)   (base fact)
             not passes(only_reads)   (absent from its completed stratum)
```

The issuer's block allows the write, and the holder's check vetoes
it. The design guarantee is worth stating in this course's terms. A
token is authorized only if `allow` holds and **every** check passes,
so appending a block appends a conjunct, and adding a conjunct can only
shrink the set of requests that succeed. Attenuation cannot escalate
for the same reason lesson 2's fixpoint cannot shrink: the structure
only moves in one direction. (The `not` here is on the service's side
of the line, over checks the service can see in full, so it is lesson
3's safe kind.)

One honest gap in the flattening: a real Biscuit **scopes** each
block's facts. Rules in the issuer's block do not see facts that a
later block asserts, so a holder cannot append `right(file2, write).`
and forge the authority. One program with one fact space has no such
wall, and exercise 3 asks you to break it.

## Where Datalog sits in the field

| System | Language | Recursion | What it buys |
|---|---|---|---|
| Binder, SecPAL, RT | Datalog plus signed statements | yes | delegation chains as derivations |
| Zanzibar and descendants | tuples plus rewrite rules | yes (nesting, inheritance) | check at global scale |
| Biscuit | Datalog inside the token | yes | offline attenuation |
| Oso (Polar) | Prolog-flavoured rules | yes, top-down | rules embedded in an application |
| Cedar (AWS) | its own policy language | no user-defined recursion | analysis by an SMT solver |

The last row is the instructive one. Cedar's designers chose a
language without user-defined recursion (hierarchy membership is a
built-in over data the application supplies), and in exchange they can
hand a whole policy set to a solver and ask questions like "can any
request be both allowed and forbidden?". That is lesson 14's trade
made in the other direction: give up recursion, and arithmetic and
complete analysis come back. The Datalog systems keep recursion and
get lesson 17's checks instead: termination, the names of cycles,
redundant rules found by containment, and a derivation for every
decision.

## The checklist, for access rules

Lesson 17's five checks apply unchanged. Authorization adds three:

1. **Default deny.** No rule should derive access from nothing. In
   Datalog that is the closed world doing its job, so the risk lies
   only in the next item.
2. **Every `not` in a granting rule is audited.** Find the authority
   for each absence and say what happens when it is unavailable.
3. **Principals are typed at the boundary.** Whatever answers "who?"
   to the outside world restricts its answers to people.

And keep the derivation of every decision you log. "Access granted"
tells an auditor nothing, but a derivation tree is the audit.

## Exercises

1. **Separation of duties.** Add `requested(R, U)` and `approved(R, U)`
   facts for expense reports, and derive `violation(R)` when someone
   approved their own request. The engine has no `!=`; say why you do
   not need one here.
2. Add a `banned(U, O)` relation that removes one person's access to
   one document, even when a group grants it. Write it once failing
   open and once failing closed, then use `--explain` to show a
   reviewer the difference.
3. Copy `programs/token.dl`, drop the holder's check, and append a
   "block 2" asserting `right(file2, write).`; then send a write
   request for `file2`. Show that the flattened program authorizes
   it, though the issuer never granted anything on `file2`. Then give
   each block its own fact space (tag every fact with its block,
   `right(0, file1, read)`, and let `allow` read only block 0) and
   show the forgery failing.
4. Count the facts `--magic` derives for a check (`can(alice, edit,
   roadmap)`) and for a list (`can(U, edit, roadmap)`). Then add ten
   more nested groups under `staff` and measure again. Which question
   gets more expensive, and why?
5. Cedar gives up recursion. Rewrite `in_group` for a world where
   groups nest at most two deep, without recursion. What did you have
   to know about the data that the recursive rule did not need?

Next: [program analysis](21-program-analysis.md), where the database
is a program and the rules ask what it might do.
