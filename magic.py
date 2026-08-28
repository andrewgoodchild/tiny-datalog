#!/usr/bin/env python3
"""
magic.py — the magic-sets transformation: goal-directed queries for a
bottom-up engine.  (Lesson 6; implementation tour in Lesson 12.)

The problem: bottom-up evaluation computes *whole relations*, but a query
like path(n5, X) only needs facts reachable from n5.  Top-down engines
(Prolog) get this focus for free by starting from the goal — at the cost
of possible non-termination.

The 1986 resolution: don't change the evaluator, change the *program*.
Given the query, rewrite the rules so that bottom-up evaluation of the
rewritten program derives only what a top-down engine would have visited.
Three ingredients:

* An **adornment** records which arguments of a predicate are bound at
  call time: path(n5, X) calls path with pattern "bf" (bound, free).
  Different call patterns get separately specialised copies of the rules,
  named pred#bf, pred#fb, ...
* A **magic predicate** magic#pred#adorn holds the bound-argument tuples
  actually demanded — "someone needs paths starting at n5".  It is seeded
  with the query's constants and grows exactly like Prolog's call stack
  would: through each rule, bindings flow left to right (a "sideways
  information passing strategy", here: the evaluator's own join order).
* Every specialised rule is **guarded** by its magic predicate, so it can
  only fire for demanded bindings.

Negation gets the simple sound treatment: a negated subgoal is never
specialised — its predicate (and everything it depends on) is included
untransformed and computed in full.  Since negative edges then point only
from the rewritten world into the original one, the rewriting is
stratified whenever the original program is.
"""

from __future__ import annotations

from collections import defaultdict

from datalog import (Atom, Const, Engine, Literal, Program, Rule, Var,
                     _aggregate_of, check_query_atom, match_answers,
                     validate)


def _adorned_name(pred, adorn):
    return "%s#%s" % (pred, adorn)


def _magic_name(pred, adorn):
    return "magic#%s#%s" % (pred, adorn)


def magic_transform(clauses, query):
    """Magic-sets rewriting of the program for `query` (an Atom, possibly
    with variables).  Returns (transformed_clauses, answer_pred): evaluate
    the transformed program and read the query's answers from answer_pred.
    """
    check_query_atom(query, validate(clauses))
    idb = {c.head.pred for c in clauses if c.body}
    # Aggregate-headed predicates are never specialised: an aggregate
    # needs its whole group, so demand restriction would change answers.
    # Like negated subgoals, they are computed in full.
    agg_preds = {c.head.pred for c in clauses
                 if c.body and _aggregate_of(c.head)}
    if query.pred not in idb or query.pred in agg_preds:
        return list(clauses), query.pred  # evaluate in full

    defs = defaultdict(list)  # IDB pred -> its clauses (rules AND facts)
    edb_facts = []
    for c in clauses:
        if c.head.pred in idb:
            defs[c.head.pred].append(c)
        else:
            edb_facts.append(c)

    # The query's own adornment: constants are bound, variables free.
    query_adorn = "".join("b" if isinstance(a, Const) else "f"
                          for a in query.args)

    out = []
    full_needed = set()   # predicates under negation: evaluate in full
    seen = set()
    # Worklist of (predicate, adornment) call patterns still to specialise.
    # Processing one pattern may discover new ones in rule bodies — exactly
    # how a top-down engine discovers subgoals.
    work = [(query.pred, query_adorn)]
    while work:
        pred, adorn = work.pop()
        if (pred, adorn) in seen:
            continue
        seen.add((pred, adorn))
        for clause in defs[pred]:
            head = clause.head
            # Variables bound on entry: those in the head's 'b' positions.
            bound_vars = {head.args[i].name
                          for i, ch in enumerate(adorn)
                          if ch == "b" and isinstance(head.args[i], Var)}
            magic_args = tuple(head.args[i]
                               for i, ch in enumerate(adorn) if ch == "b")
            # `prefix` = the magic guard + body literals transformed so
            # far.  A snapshot of it, taken just before an IDB subgoal, is
            # that subgoal's demand context: "if evaluation got this far,
            # these bindings are being asked for."
            prefix = [Literal(Atom(_magic_name(pred, adorn), magic_args))]
            negatives = []
            for lit in clause.body:
                if lit.negated:
                    negatives.append(lit)  # untouched; defined in full
                    if lit.atom.pred in idb:
                        full_needed.add(lit.atom.pred)
                    continue
                if lit.atom.pred in agg_preds:
                    prefix.append(lit)   # aggregate: keep original name
                    full_needed.add(lit.atom.pred)
                elif lit.atom.pred in idb:
                    # Adorn the subgoal from what is bound *right now*.
                    sub = "".join(
                        "b" if isinstance(a, Const) or a.name in bound_vars
                        else "f"
                        for a in lit.atom.args)
                    sub_bound = tuple(a for a, ch in zip(lit.atom.args, sub)
                                      if ch == "b")
                    # Magic rule: this subgoal's bindings are demanded
                    # whenever the prefix so far succeeds.
                    out.append(Rule(Atom(_magic_name(lit.atom.pred, sub),
                                         sub_bound),
                                    tuple(prefix)))
                    work.append((lit.atom.pred, sub))
                    prefix.append(
                        Literal(Atom(_adorned_name(lit.atom.pred, sub),
                                     lit.atom.args)))
                else:
                    prefix.append(lit)  # EDB literal: kept as-is
                # A positive literal, once joined, binds all its variables
                # (aggregate heads included: their tuples are ordinary)
                # for everything to its right — the evaluator's own order.
                bound_vars |= {a.name for a in lit.atom.args
                               if isinstance(a, Var)}
            # The specialised rule: original head under its adorned name,
            # guarded by magic, negatives at the end (they only filter).
            out.append(Rule(Atom(_adorned_name(pred, adorn), head.args),
                            tuple(prefix) + tuple(negatives)))

    # Include negated subgoals' definitions untransformed, transitively.
    stack = list(full_needed)
    included = set()
    while stack:
        p = stack.pop()
        if p in included:
            continue
        included.add(p)
        for c in defs[p]:
            out.append(c)
            for lit in c.body:
                if lit.atom.pred in idb and lit.atom.pred not in included:
                    stack.append(lit.atom.pred)

    # Seed the query's magic predicate with the query constants, keep EDB.
    seed_args = tuple(a for a in query.args if isinstance(a, Const))
    out.append(Rule(Atom(_magic_name(query.pred, query_adorn), seed_args), ()))
    out.extend(edb_facts)

    # The same magic rule can be generated from several adornment passes;
    # rules are hashable (frozen dataclasses), so dedupe preserving order.
    return list(dict.fromkeys(out)), _adorned_name(query.pred, query_adorn)


def magic_query(clauses, query):
    """Answer `query` via magic-sets rewriting + semi-naive evaluation.
    Returns (engine, answers): the engine that ran the rewritten program,
    and the set of ground tuples matching the query."""
    transformed, answer_pred = magic_transform(clauses, query)
    engine = Engine(Program(transformed))
    engine.run()
    answers = set(match_answers(query, engine.rels.get(answer_pred, ())))
    return engine, answers
