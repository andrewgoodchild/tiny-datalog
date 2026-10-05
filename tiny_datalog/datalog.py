#!/usr/bin/env python3
"""
datalog.py — the base engine: a small Datalog evaluator with semi-naive
evaluation and stratified negation.  Pure standard-library Python.

The language itself — syntax, AST, parser, safety validation and
stratification — lives in core.py, whose docstring also describes the
three tiers of the package (core, engines, extensions).  This file is
the base engine built on it: the bottom-up evaluator, aggregation,
--explain / why-not, and the CLI.  Every name core.py defines is
re-exported here too, so `from tiny_datalog.datalog import parse` keeps
working.

Semantics
---------
* Safety and stratified negation: checked by core.py before evaluation
  starts (see its docstring); a program that fails either check never
  reaches the evaluator.
* Semi-naive evaluation: each stratum is evaluated to fixpoint; after the
  first round, recursive rules are re-evaluated only with the previous
  round's new facts (the "delta") substituted into each recursive body
  position in turn, instead of recomputing every join from scratch.
* Magic sets: with --magic, each query is answered by first rewriting the
  program (adornments + magic predicates, left-to-right sideways
  information passing) so that bottom-up evaluation only derives facts
  relevant to the query's bound arguments — goal-directed evaluation
  without giving up semi-naive.  Negated subgoals are not specialised:
  their predicates are included untransformed and computed in full, which
  keeps the rewriting stratified whenever the original program is.
  (Implementation: magic.py.)

Stratifiability is a *syntactic* condition; rejection by the stratified
engine does not by itself mean a program is semantically paradoxical.
For small programs, `--models` grounds the program and reports the
semantic story: all stable models (by exhaustive search) and the
well-founded (three-valued) model.  (Implementation: semantics.py.)

The Under the hood sections of lessons 1-3 are a guided tour of how it
all works, reading core.py and this file together.

CLI
---
    python3 datalog.py program.dl               # print derived relations
    python3 datalog.py --trace program.dl       # + strata and per-round deltas
    python3 datalog.py -q 'eats_in_cafe(X)' program.dl
    python3 datalog.py --magic -q 'path(n5, X)' program.dl   # goal-directed
    python3 datalog.py --engine tabling -q 'path(n5, X)' program.dl
                                    # any engine in engines.py's ENGINES
    python3 datalog.py --models program.dl      # stable + well-founded models
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections import defaultdict

# The language — AST, errors, parser, validation, stratification,
# matching, formatting, query helpers, CLI plumbing — comes from core.py.
# Every name below used to be defined in this file, and is imported
# under its old name too (underscored ones included), so code written
# against `tiny_datalog.datalog` keeps working: this list *is* the
# re-export, and nothing in it may be dropped as "unused".
from tiny_datalog.core import (  # noqa: F401 -- re-exported
    # AST and errors
    Var, Const, Struct, Atom, Literal, Rule,
    DatalogError, ParseError, SafetyError, StratificationError,
    # parser
    parse, parse_goal, _Parser, _TOKEN, _tokenize, _num, _shown,
    # validation and stratification
    AGGREGATES, aggregate_of, _aggregate_of, validate,
    stratify, _tarjan, _find_cycle, _format_cycle,
    # matching
    match, _match, _MISSING, _EMPTY,
    # facts from Python data
    python_facts, _PREDICATE,
    # values: sorting and formatting
    sort_key, _sort_key, format_atom, format_fact, _format_value,
    # queries
    check_query_atom, parse_query_atom, _parse_query_atom, match_answers,
    # command-line plumbing
    read_program, cli,
)


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class Program:
    def __init__(self, clauses):
        for c in clauses:
            if c.retract:
                raise SafetyError(
                    "retraction (%s) is an update, not a statement — a "
                    "static program simply wouldn't assert the fact.  "
                    "Apply it to a live materialisation via incremental.py."
                    % c)
        self.arity = validate(clauses)
        self.facts = [r for r in clauses if not r.body]
        self.rules = [r for r in clauses if r.body]
        self.idb = {r.head.pred for r in self.rules}
        self.strata = stratify(clauses)


class Engine:
    """Bottom-up, stratum-by-stratum semi-naive evaluator.

    Data representation, in full: `rels` maps each predicate name to a
    Python set of ground tuples — path -> {("a","b"), ("a","c")}.  That's
    the whole database.  Rules never delete (Datalog is monotone within a
    stratum), so evaluation is: grow these sets until one full pass adds
    nothing.  Strata are computed once, then processed in order, so by
    the time a negated literal is consulted its relation is finished."""

    def __init__(self, program, naive=False):
        self.program = program
        self.naive = naive            # True: skip the delta discipline
        self.rels = defaultdict(set)  # pred -> set of ground tuples
        self.stats = []               # per-stratum iteration statistics
        # derivation-order stamps: base facts 0, then one tick per
        # absorbed round — --explain uses these to build well-founded
        # derivation trees (a fact's premises always carry lower stamps)
        self.first_seen = {}
        self._stamp = 0
        # cumulative evaluation seconds per rule (--trace reports the
        # hottest ones -- the join that is eating your run)
        self.rule_time = defaultdict(float)

    def run(self):
        for fact in self.program.facts:
            tup = tuple(a.value for a in fact.head.args)
            self.rels[fact.head.pred].add(tup)
            self.first_seen.setdefault((fact.head.pred, tup), 0)
        by_stratum = defaultdict(list)
        for rule in self.program.rules:
            by_stratum[self.program.strata[rule.head.pred]].append(rule)
        for level in sorted(by_stratum):
            self._eval_stratum(level, by_stratum[level])
        return self.rels

    def _eval_stratum(self, level, rules):
        preds = {r.head.pred for r in rules}
        stat = {"stratum": level, "preds": sorted(preds), "iterations": []}
        self.stats.append(stat)
        if self.naive:
            self._eval_stratum_naive(rules, stat)
            return

        # Round 1: evaluate every rule of the stratum against the full db.
        delta, _produced = self._full_round(rules)
        self._absorb(delta, stat)

        # Recursive rules: a positive body literal names a stratum predicate.
        recursive = []
        for rule in rules:
            occs = [i for i, lit in enumerate(rule.body)
                    if not lit.negated and lit.atom.pred in preds]
            if occs:
                recursive.append((rule, occs))

        # Semi-naive rounds: substitute the previous round's delta into each
        # recursive position in turn; every other literal reads the full
        # (already-updated) relations, so no new derivation is missed and
        # nothing is recomputed from only-old facts.
        while delta:
            new_delta = defaultdict(set)
            for rule, occs in recursive:
                head = rule.head.pred
                t0 = time.perf_counter()
                for i in occs:
                    if not delta.get(rule.body[i].atom.pred):
                        continue
                    for tup in self.eval_rule(rule, delta_occ=i, delta=delta):
                        if tup not in self.rels[head]:
                            new_delta[head].add(tup)
                self.rule_time[rule] += time.perf_counter() - t0
            delta = new_delta
            self._absorb(delta, stat)

    def _eval_stratum_naive(self, rules, stat):
        """Naive evaluation: every rule against the whole database, every
        round, until nothing new appears — no delta discipline, so every
        already-known fact is re-derived every round.  Deliberately
        wasteful: run --naive --trace beside the default to watch
        semi-naive earn its name (Lesson 2)."""
        stat["produced"] = []   # total tuples derived per round
        while True:
            delta, produced = self._full_round(rules)
            stat["produced"].append(produced)
            self._absorb(delta, stat)
            if not delta:
                return

    def _full_round(self, rules):
        """One round of every rule against the whole database — semi-
        naive's round 1, and *every* round of naive evaluation (naive is
        just round 1, repeated until nothing changes).  Returns (delta,
        produced): the genuinely new tuples per predicate, and how many
        tuples the rules derived in all, old ones included — the waste
        --naive --trace puts on display.  Time spent is charged to each
        rule for the per-rule profile."""
        delta = defaultdict(set)
        produced = 0
        for rule in rules:
            t0 = time.perf_counter()
            for tup in self._produce(rule):
                produced += 1
                if tup not in self.rels[rule.head.pred]:
                    delta[rule.head.pred].add(tup)
            self.rule_time[rule] += time.perf_counter() - t0
        return delta, produced

    def _produce(self, rule):
        """All head tuples one rule derives right now (aggregate-aware)."""
        if aggregate_of(rule.head):
            return self._eval_aggregate(rule)
        return self.eval_rule(rule)

    def _absorb(self, delta, stat):
        self._stamp += 1
        for pred, tuples in delta.items():
            self.rels[pred] |= tuples
            for t in tuples:
                self.first_seen.setdefault((pred, t), self._stamp)
        stat["iterations"].append(
            {p: len(ts) for p, ts in delta.items() if ts})

    def substitutions(self, rule, delta_occ=None, delta=None, seed=None):
        """Every substitution satisfying the rule body (positives joined
        first — they bind; negatives filter afterwards, against fully
        computed lower strata).  If delta_occ is given, the positive
        literal at that body index reads from `delta` instead of the
        full relations — the semi-naive restriction.  A `seed`
        substitution pre-binds variables (--explain uses this).
        Public because extensions reuse this join over a database they
        filled themselves: semantics.py grounds rules with it, and
        defeasible.py instantiates rules against a fact base."""
        # Positives first (they bind variables), negatives filter afterwards.
        ordered = sorted(range(len(rule.body)),
                         key=lambda i: rule.body[i].negated)
        substs = [dict(seed) if seed else {}]
        for i in ordered:
            lit = rule.body[i]
            if not substs:
                return []
            if delta_occ is not None and i == delta_occ:
                rel = delta.get(lit.atom.pred, _EMPTY)
            else:
                rel = self.rels.get(lit.atom.pred, _EMPTY)
            substs = self._join_step(lit, substs, rel)
        return substs

    def _join_step(self, lit, substs, rel):
        """Carry every substitution across one body literal, reading the
        relation `rel`.  A positive literal is a join: each substitution
        extends once per tuple it matches (and may bind new variables).
        A negated literal only filters: its atom is ground by now, and
        the substitution survives if that fact is absent.  why-not
        (whynot) walks a body with this same step, to see where it dies."""
        if lit.negated:
            return [s for s in substs
                    if self.instantiate(lit.atom, s) not in rel]
        args = lit.atom.args
        new = []
        for s in substs:
            for tup in rel:
                m = match(args, tup, s)
                if m is not None:
                    new.append(m)
        return new

    def eval_rule(self, rule, delta_occ=None, delta=None):
        """Yield head tuples derivable from one rule (with delta_occ and
        delta, the semi-naive restriction of substitutions).
        incremental.py drives its own insert rounds with this."""
        for s in self.substitutions(rule, delta_occ, delta):
            yield self.instantiate(rule.head, s)

    def _eval_aggregate(self, rule):
        """Aggregate rules — total(P, sum(A)) :- charge(P, C, A). — group
        the body's distinct *solutions* by the plain head arguments and
        fold the aggregate over each group.  Set semantics applies to
        solutions (rows), not to the aggregated values: two different
        charges of 50 sum to 100, and count gives the same answer
        whichever bound variable you name — matching SQL and Soufflé.
        Stratification has already guaranteed the body relations are
        complete (aggregation edges are strict, like negation), so one
        evaluation suffices."""
        idx, func, _var = aggregate_of(rule.head)
        for key, values in self._aggregate_groups(rule).items():
            out = list(key)
            out.insert(idx, _fold(func, values, rule))
            yield tuple(out)

    def _aggregate_groups(self, rule):
        """{group key: [aggregated value per distinct body solution]} for
        an aggregate rule; the key is the head's plain arguments."""
        idx, _func, var = aggregate_of(rule.head)
        groups = defaultdict(list)
        # solutions are distinct already: each binds every body var, `_` too
        for s in self.substitutions(rule):
            key = tuple(a.value if isinstance(a, Const) else s[a.name]
                        for j, a in enumerate(rule.head.args) if j != idx)
            groups[key].append(s[var.name])
        return groups

    def query(self, goal):
        """The answers to a query, one dict per answer, in sorted order:

            engine.query("exposed(S, C)")
            -> [{"S": "pkg0", "C": "cve_2026_0001"}, ...]

        `goal` is query text or an Atom.  Anonymous variables are left
        out of the answers; a query with no variables answers [{}] if it
        holds and [] if it does not."""
        atom = parse_goal(goal) if isinstance(goal, str) else goal
        check_query_atom(atom, self.program.arity)
        names = []
        for a in atom.args:
            if isinstance(a, Var) and not a.anonymous and a.name not in names:
                names.append(a.name)
        rows = {tuple(s[n] for n in names)
                for s in (match(atom.args, tup, {})
                          for tup in self.rels.get(atom.pred, ()))
                if s is not None}
        return [dict(zip(names, row)) for row in sorted(rows, key=sort_key)]

    def answers(self, atom):
        """The set of ground tuples matching a query Atom — the engine
        interface every strategy in engines.py shares.  Read from the
        materialised relations, so call run() first.  (query() above is
        the friendlier form for library users: text in, dicts out.)"""
        check_query_atom(atom, self.program.arity)
        return set(match_answers(atom, self.rels.get(atom.pred, ())))

    @staticmethod
    def instantiate(atom, subst):
        """The ground tuple an atom becomes under a substitution that
        binds all its variables — a rule head once its body is solved."""
        return tuple(a.value if isinstance(a, Const) else subst[a.name]
                     for a in atom.args)

    # The names these had while they were private; kept so that code
    # written against the old names still works.
    _rule_substitutions = substitutions
    _eval_rule = eval_rule
    _instantiate = instantiate


def _fold(func, values, rule):
    """Fold one group's values with count, sum, min, or max."""
    try:
        if func == "count":
            agg = len(values)
        elif func == "sum":
            agg = sum(values)
        elif func == "min":
            agg = min(values)
        else:
            agg = max(values)
    except TypeError:
        raise DatalogError(
            "cannot %s over mixed or non-numeric values in: %s"
            % (func, rule))
    except OverflowError:   # e.g. a float added to an int beyond its range
        raise DatalogError("%s overflowed in: %s" % (func, rule))
    if isinstance(agg, float) and not math.isfinite(agg):
        # a float sum can overflow; inf would print as a constant named inf
        raise DatalogError("%s gives %s, which is not a finite number, in: %s"
                           % (func, agg, rule))
    return agg


def run_program(text, facts=None):
    """Parse, stratify, and evaluate a program; return the Engine.

    `facts` adds base facts from Python data, so rows from a CSV file or
    a database query can feed the rules without first being written out
    as Datalog text:

        run_program(rules, facts={"depends": [("pkg4", "pkg13")],
                                  "service": ["pkg4"]})

    Each row is a tuple of str, int or float (a bare value is a one-
    column row), and every fact is checked exactly as if it had been
    parsed: arity, groundness, and agreement with the rules."""
    engine = Engine(Program(parse(text) + python_facts(facts or {})))
    engine.run()
    return engine


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _print_strata(program):
    levels = defaultdict(list)
    for pred, level in program.strata.items():
        levels[level].append("%s/%d" % (pred, program.arity[pred]))
    print("Stratification:")
    for level in sorted(levels):
        print("  stratum %d: %s" % (level, ", ".join(sorted(levels[level]))))


def _print_stats(engine):
    print("Naive evaluation:" if engine.naive else "Semi-naive evaluation:")
    for stat in engine.stats:
        print("  stratum %d (%s):" % (stat["stratum"], ", ".join(stat["preds"])))
        produced = stat.get("produced")
        for n, round_ in enumerate(stat["iterations"], 1):
            extra = ""
            if produced and n <= len(produced):
                extra = "   (%d tuples derived)" % produced[n - 1]
            if round_:
                deltas = ", ".join("+%d %s" % (c, p)
                                   for p, c in sorted(round_.items()))
                print("    round %d: %s%s" % (n, deltas, extra))
            else:
                print("    round %d: no new facts — fixpoint%s" % (n, extra))
        sizes = ", ".join("%s=%d" % (p, len(engine.rels.get(p, ())))
                          for p in stat["preds"])
        print("    sizes: %s" % sizes)
    hot = sorted(engine.rule_time.items(), key=lambda kv: -kv[1])[:3]
    if hot and hot[0][1] >= 0.01:
        print("  hottest rules:")
        total = sum(engine.rule_time.values()) or 1.0
        for rule, secs in hot:
            print("    %5.2fs  (%2.0f%%)  %s"
                  % (secs, 100 * secs / total, rule))


def _atom_sort_key(atom):
    pred, args = atom
    return (pred, sort_key(args))


def _format_atoms(atoms):
    return "  ".join(format_fact(p, t)
                     for p, t in sorted(atoms, key=_atom_sort_key))


def _print_models(clauses):
    """Report the semantic story: stable models and the well-founded model."""
    from tiny_datalog.semantics import (
        ground_program, stable_models, well_founded)
    try:
        stratify(clauses)
        print("Syntactic check: stratifiable.")
    except StratificationError as exc:
        print("Syntactic check: not stratifiable (%s)." % _format_cycle(exc.cycle))
        print("  (Syntactic only — an unstratifiable program may still have "
              "stable models.)")
    grounding = ground_program(clauses)
    facts = grounding[0]
    try:
        models = stable_models(clauses, grounding=grounding)
    except DatalogError as exc:
        # too big for exhaustive search -- but the well-founded model
        # below takes polynomial time, so it is still worth reporting
        print("Stable models: search skipped (%s)." % exc)
        models = None
    if models == []:
        print("Stable models: none — no consistent two-valued model exists.")
    elif models:
        print("Stable models: %d" % len(models))
        for i, m in enumerate(
                sorted(models, key=lambda m: _format_atoms(m - facts)), 1):
            print("  model %d: %s" % (i, _format_atoms(m - facts)
                                      or "(EDB facts only)"))
    true, undef = well_founded(clauses, grounding=grounding)
    print("Well-founded model (three-valued):")
    print("  true:      %s" % (_format_atoms(true - facts) or "(EDB facts only)"))
    print("  undefined: %s" % (_format_atoms(undef) or "(none)"))
    return 0


def _print_answers(atom, tuples, suffix=""):
    print("?- %s%s" % (atom, suffix))
    answers = sorted(tuples, key=sort_key)
    for tup in answers:
        print("   " + format_fact(atom.pred, tup))
    print("   (%d answer%s)" % (len(answers), "" if len(answers) == 1 else "s"))


# ---------------------------------------------------------------------------
# --explain: derivation trees
# ---------------------------------------------------------------------------
# Ask the engine WHY it believes a fact.  The trick that keeps the tree
# well-founded: every fact carries a derivation-order stamp (Engine
# first_seen), and its first derivation necessarily used premises with
# strictly smaller stamps — so searching for a rule instance whose
# positive premises all precede the fact always succeeds and can never
# justify a fact by itself.

def _derivation_of(engine, pred, tup, index=None):
    """A (rule, premises) justification for a derived fact, where every
    positive premise strictly precedes it in derivation order; None for
    base facts.  premises is a list of (literal, ground_tuple).  `index`
    is a lookup cache shared across one explanation (see _earlier_solution)."""
    stamp = engine.first_seen.get((pred, tup), 0)
    if stamp == 0:
        return None     # stated in the program, whatever rules also say
    index = {} if index is None else index
    for rule in engine.program.rules:
        if rule.head.pred != pred:
            continue
        if aggregate_of(rule.head):
            group = _aggregate_group(engine, rule, tup, index)
            if group is not None:
                return rule, group
            continue
        seed = match(rule.head.args, tup, {})
        if seed is None:
            continue
        s = _earlier_solution(engine, rule, seed, stamp, index)
        if s is not None:
            return rule, [(lit, engine.instantiate(lit.atom, s))
                          for lit in rule.body]
    return None


def _earlier_solution(engine, rule, seed, stamp, index):
    """One body solution extending `seed` whose positive premises all
    carry stamps below `stamp`, or None.  The evaluator's join scans
    whole relations, which is fine once per round but far too slow once
    per tree node — a 400-step chain would cost 400 full joins.  So this
    join takes the head's bindings first, always picks next the positive
    literal with the most arguments already known, and looks its matches
    up in a hash index (built once per relation and pattern of known
    positions, then reused down the tree).  Negatives filter at the end."""
    positives = [lit for lit in rule.body if not lit.negated]
    substs = [seed]
    known = set(seed)

    def is_known(a):
        return isinstance(a, Const) or a.name in known

    while positives and substs:
        lit = max(positives, key=lambda l: sum(map(is_known, l.atom.args)))
        positives.remove(lit)
        args, pred = lit.atom.args, lit.atom.pred
        cols = tuple(j for j, a in enumerate(args) if is_known(a))
        table = _index_on(engine, index, pred, cols)
        new = []
        for s in substs:
            key = tuple(args[j].value if isinstance(args[j], Const)
                        else s[args[j].name] for j in cols)
            for t in table.get(key, ()):
                if engine.first_seen.get((pred, t), 0) < stamp:
                    m = match(args, t, s)
                    if m is not None:
                        new.append(m)
        substs = new
        known |= {a.name for a in args if isinstance(a, Var)}
    for s in substs:
        if all(engine.instantiate(lit.atom, s)
               not in engine.rels.get(lit.atom.pred, _EMPTY)
               for lit in rule.body if lit.negated):
            return s
    return None


def _index_on(engine, index, pred, cols):
    """pred's tuples grouped by their values at positions `cols`."""
    if (pred, cols) not in index:
        table = defaultdict(list)
        for t in engine.rels.get(pred, _EMPTY):
            table[tuple(t[j] for j in cols)].append(t)
        index[pred, cols] = table
    return index[pred, cols]


def _group_values(engine, rule, tup, index=None):
    """The aggregated values (one per distinct body solution) of the
    group that head tuple `tup` belongs to; [] if the group is empty.
    The rule's groups are computed once per `index` cache."""
    index = {} if index is None else index
    if rule not in index:
        index[rule] = engine._aggregate_groups(rule)
    idx = aggregate_of(rule.head)[0]
    key = tuple(v for j, v in enumerate(tup) if j != idx)
    return index[rule].get(key, [])


def _aggregate_group(engine, rule, tup, index=None):
    """If this aggregate rule computes exactly `tup` — its group exists
    *and* folds to tup's value — the contributing values, presented as a
    pseudo-premise; otherwise None."""
    idx, func, var = aggregate_of(rule.head)
    values = _group_values(engine, rule, tup, index)
    if not values or _fold(func, values, rule) != tup[idx]:
        return None
    shown = ", ".join(_format_value(v) for v in
                      sorted(values, key=lambda x:
                             (0, x) if isinstance(x, (int, float))
                             else (1, str(x))))
    return [("aggregate", "%s over %d body solution%s of %s: [%s]"
             % (func, len(values), "" if len(values) == 1 else "s", var,
                shown))]


def explain(engine, pred, tup):
    """Build an indented derivation tree for one fact; returns the lines.
    Depth-first with an explicit stack rather than recursion, so a long
    derivation chain can't hit Python's recursion limit (the same reason
    _tarjan is iterative).  Stack entries are (indent, pred, tup) for a
    fact still to explain, or (indent, None, text) for a finished line."""
    lines, shown, index = [], set(), {}
    stack = [(0, pred, tup)]
    while stack:
        indent, pred, tup = stack.pop()
        pad = "  " * indent
        if pred is None:
            lines.append(pad + tup)
            continue
        label = format_atom(pred, tup)
        if (pred, tup) in shown:
            lines.append("%s%s   (derivation shown above)" % (pad, label))
            continue
        derivation = _derivation_of(engine, pred, tup, index)
        if derivation is None:
            lines.append("%s%s   (base fact)" % (pad, label))
            continue
        shown.add((pred, tup))
        rule, premises = derivation
        lines.append("%s%s   [via %s]" % (pad, label, rule))
        children = []
        for item in premises:
            if item[0] == "aggregate":
                children.append((indent, None, "  = %s" % item[1]))
            elif item[0].negated:
                children.append((indent, None,
                                 "  not %s   (absent from its completed "
                                 "stratum)" % format_atom(item[0].atom.pred,
                                                          item[1])))
            else:
                children.append((indent + 1, item[0].atom.pred, item[1]))
        stack.extend(reversed(children))   # so the first premise pops first
    return lines


def whynot(engine, pred, tup, lines=None):
    """Why is this ground fact NOT derived?  For each rule that could
    head it, walk the body in evaluation order and report the first
    literal the join dies at.  When the blocker is a negated literal,
    the negated atom *holds* -- so its positive derivation is the
    culprit, and it is explained inline (the complement's why)."""
    lines = [] if lines is None else lines
    label = format_atom(pred, tup)
    rules = [r for r in engine.program.rules if r.head.pred == pred]
    if not rules:
        lines.append("%s is not a stated fact, and no rule derives %s."
                     % (label, pred))
        return lines
    lines.append("%s is not derived.  Per rule:" % label)
    headless = 0
    for rule in rules:
        if aggregate_of(rule.head):
            idx, func, _var = aggregate_of(rule.head)
            values = _group_values(engine, rule, tup)
            lines.append("  via %s" % rule)
            if not values:
                lines.append("    blocked: no body solutions produce this "
                             "group (an empty group yields no fact)")
            else:
                lines.append("    blocked: the group exists, but its %s is "
                             "%s, not %s" % (func,
                                             _format_value(_fold(func, values, rule)),
                                             _format_value(tup[idx])))
            continue
        seed = match(rule.head.args, tup, {})
        if seed is None:
            headless += 1
            continue
        lines.append("  via %s" % rule)
        substs = [dict(seed)]
        ordered = sorted(range(len(rule.body)),
                         key=lambda i: rule.body[i].negated)
        blocked = None
        for i in ordered:
            lit = rule.body[i]
            survivors = engine._join_step(
                lit, substs, engine.rels.get(lit.atom.pred, _EMPTY))
            if not survivors:
                blocked = (lit, substs[0])
                break
            substs = survivors
        if blocked is None:
            lines.append("    (this rule does derive it -- "
                         "the fact should exist; please report)")
            continue
        lit, s = blocked
        shown = Atom(lit.atom.pred,
                     tuple(Const(s[a.name]) if isinstance(a, Var)
                           and a.name in s else a for a in lit.atom.args))
        if lit.negated:
            inst = engine.instantiate(lit.atom, s)
            lines.append("    blocked at: not %s -- %s holds:"
                         % (shown, format_atom(lit.atom.pred, inst)))
            for l in explain(engine, lit.atom.pred, inst):
                lines.append("      " + l)
        else:
            lines.append("    blocked at: %s -- no matching fact" % shown)
    if headless:
        lines.append("  (%d rule%s for %s cannot match this head and "
                     "%s skipped)" % (headless, "" if headless == 1 else "s",
                                      pred,
                                      "was" if headless == 1 else "were"))
    return lines


def _run_explain(q, engine):
    atom = parse_query_atom(q, engine.program.arity)
    matches = sorted(match_answers(atom, engine.rels.get(atom.pred, ())),
                     key=sort_key)
    print("?- explain %s" % atom)
    if not matches:
        if all(isinstance(a, Const) for a in atom.args):
            tup = tuple(a.value for a in atom.args)
            for line in whynot(engine, atom.pred, tup):
                print("   " + line)
        else:
            print("   (no matching facts)")
        return
    for tup in matches:
        for line in explain(engine, atom.pred, tup):
            print("   " + line)


def _run_query(q, engine):
    atom = parse_query_atom(q, engine.program.arity)
    _print_answers(atom, match_answers(atom, engine.rels.get(atom.pred, ())))


def _run_magic_query(q, clauses, trace):
    from tiny_datalog.magic import magic_transform
    atom = parse_query_atom(q)
    transformed, answer_pred = magic_transform(clauses, atom)
    mprog = Program(transformed)
    mengine = Engine(mprog)
    if trace:
        print("Magic-sets rewriting (answer predicate %s):" % answer_pred)
        for c in transformed:
            print("  %s" % c)
        print()
        _print_strata(mprog)
        print()
    mengine.run()
    if trace:
        _print_stats(mengine)
        magic_total = sum(len(mengine.rels.get(p, ())) for p in mprog.idb)
        try:
            fengine = Engine(Program(clauses))
            fengine.run()
            full_total = sum(len(fengine.rels.get(p, ()))
                             for p in fengine.program.idb)
            print("[magic] %d IDB facts derived vs %d under full evaluation"
                  % (magic_total, full_total))
        except StratificationError:
            print("[magic] %d IDB facts derived (no full-evaluation baseline: "
                  "the original program is not stratifiable)" % magic_total)
        except DatalogError as exc:
            print("[magic] %d IDB facts derived (no full-evaluation baseline: "
                  "%s)" % (magic_total, exc))
        print()
    _print_answers(atom, match_answers(atom, mengine.rels.get(answer_pred, ())),
                   suffix="   [magic]")


def _run_tabled_queries(queries, clauses, trace):
    """-q under --engine tabling, through the engines.py interface.  The
    answers print exactly as every other engine's do; --trace adds the
    size of the work, and tabling.py --tables lists the tables."""
    from tiny_datalog.engines import ENGINES
    tabled = ENGINES["tabling"](clauses)
    for q in queries:
        atom = parse_query_atom(q, tabled.engine.arity)
        _print_answers(atom, tabled.answers(atom), suffix="   [tabled]")
        if trace:
            print("[tabling] %d subgoal table%s, filled in %d round%s "
                  "(tabling.py --tables lists them)"
                  % (len(tabled.engine.tables),
                     "" if len(tabled.engine.tables) == 1 else "s",
                     tabled.engine.rounds,
                     "" if tabled.engine.rounds == 1 else "s"))
            print()


# The --engine choices, in engines.py's order.  Spelled out rather than
# imported: engines.py imports this module, so this module can only
# import it lazily, inside a function — and a test pins the two lists
# together.
ENGINE_NAMES = ["seminaive", "naive", "magic", "tabling"]


def _engine_choice(args):
    """The engine the flags ask for, or None after reporting a conflict.
    --naive and --magic predate --engine and are its shorthands; given
    together, --magic wins, as it always has (naive evaluation of a
    magic-rewritten program was never on offer)."""
    implied = "magic" if args.magic else "naive" if args.naive else None
    if args.engine and implied and args.engine != implied:
        print("error: --%s contradicts --engine %s" % (implied, args.engine),
              file=sys.stderr)
        return None
    return args.engine or implied or "seminaive"


@cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="A small Datalog engine with semi-naive evaluation "
                    "and stratified negation.")
    ap.add_argument("file", help="Datalog program (.dl)")
    ap.add_argument("-t", "--trace", action="store_true",
                    help="print stratification and per-round delta statistics")
    ap.add_argument("-a", "--all", action="store_true",
                    help="print EDB (input) relations too, not just derived ones")
    ap.add_argument("-q", "--query", action="append", default=[], metavar="ATOM",
                    help="query, e.g. 'eats_in_cafe(X)' (repeatable)")
    ap.add_argument("-m", "--models", action="store_true",
                    help="skip stratified evaluation; instead ground the "
                         "program and report all stable models (exhaustive "
                         "search, small programs only) and the well-founded "
                         "three-valued model")
    ap.add_argument("--naive", action="store_true",
                    help="evaluate naively (no delta discipline); with "
                         "--trace, prints tuples-derived per round so the "
                         "semi-naive comparison is measurable")
    ap.add_argument("-e", "--explain", action="append", default=[],
                    metavar="ATOM",
                    help="print a derivation tree for every fact matching "
                         "the atom (repeatable)")
    ap.add_argument("-M", "--magic", action="store_true",
                    help="answer each -q query via the magic-sets rewriting "
                         "(goal-directed: only facts relevant to the query's "
                         "bound arguments are derived); with --trace, also "
                         "print the rewritten program and derivation counts")
    ap.add_argument("--engine", choices=ENGINE_NAMES, default=None,
                    help="evaluation strategy (default seminaive; see "
                         "engines.py).  All four give the same answers.  "
                         "seminaive and naive materialise every relation, "
                         "so they also print whole relations and support "
                         "--explain; magic and tabling are goal-directed: "
                         "they answer -q queries only and refuse "
                         "--explain, which reads a derivation tree off a "
                         "full materialisation.  --trace shows each "
                         "engine's own work: rounds and deltas, the "
                         "rewritten program, or the count of subgoal "
                         "tables.  --naive and --magic are short for "
                         "--engine naive and --engine magic")
    args = ap.parse_args(argv)
    engine_name = _engine_choice(args)
    if engine_name is None:
        return 1

    # every mode re-validates via Program / magic_transform /
    # ground_program, so parsing is all that must happen up front;
    # a DatalogError anywhere below is reported by @cli
    clauses = parse(read_program(args.file))

    if args.models:
        return _print_models(clauses)

    if engine_name in ("magic", "tabling"):
        flag = "--magic" if args.magic else "--engine %s" % engine_name
        if not args.query:
            print("error: %s requires at least one -q/--query" % flag,
                  file=sys.stderr)
            return 1
        if args.explain:
            print("error: --explain needs a bottom-up engine (seminaive or "
                  "naive): a derivation tree is read off the full "
                  "materialisation, which %s does not build" % flag,
                  file=sys.stderr)
            return 1
        try:
            if engine_name == "magic":
                for q in args.query:
                    _run_magic_query(q, clauses, args.trace)
            else:
                _run_tabled_queries(args.query, clauses, args.trace)
        except StratificationError as exc:
            print("REJECTED: %s" % exc, file=sys.stderr)
            return 2
        return 0

    try:
        program = Program(clauses)
    except StratificationError as exc:
        print("REJECTED: %s" % exc, file=sys.stderr)
        print("(This is a syntactic verdict.  Run with --models for the "
              "semantic one: stable models and the well-founded model.)",
              file=sys.stderr)
        return 2

    engine = Engine(program, naive=engine_name == "naive")
    if args.trace:
        _print_strata(program)
        print()
    engine.run()      # may raise DatalogError, e.g. sum over a non-number
    if args.trace:
        _print_stats(engine)
        print()

    if args.query or args.explain:
        for q in args.query:
            _run_query(q, engine)
        for q in args.explain:
            _run_explain(q, engine)
        return 0

    preds = sorted(set(program.arity) if args.all else program.idb)
    for pred in preds:
        tuples = engine.rels.get(pred, set())
        kind = "derived" if pred in program.idb else "input"
        print("%% %s/%d (%s) — %d fact%s" %
              (pred, program.arity[pred], kind, len(tuples),
               "" if len(tuples) == 1 else "s"))
        for tup in sorted(tuples, key=sort_key):
            print(format_fact(pred, tup))
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
