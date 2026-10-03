"""tiny-datalog as a `datalog-conformance` evaluator.

datalog-conformance (https://pypi.org/project/datalog-conformance/) is
a corpus of Datalog programs harvested from Souffle, Nemo and Crepe,
with the answers those engines give.  Its surface syntax is
Souffle-style, not ours:

    theirs                          ours
    ------------------------------  ------------------------------
    Y(a,c) :- X(a,b), Y(b,c).       p_Y(V_a, V_c) :- p_X(V_a, V_b), ...
    any bare name in an argument    a variable (capitalised here)
    "str", 42                       unchanged
    Ok() :- not Ok()                p_Ok :- not p_Ok.

so rules are translated token by token, predicates are prefixed `p_`
(our predicates must start lowercase) and prefixed back on the way out.

One rewrite goes beyond spelling.  Nemo accepts a variable that occurs
only under `not` -- `not s3(X, 5, P)` -- reading it as "there is no P".
This engine refuses that rule on purpose (Lesson 3, Lesson 17: the
reading is ambiguous until you say which one you meant), and the fix
the lessons prescribe is to project first:

    aux1(X) :- s3(X, 5, P).        ...  not aux1(X)

The adapter applies exactly that fix -- but only to cases harvested from
Nemo or Souffle, the engines whose reading it reproduces.  The corpus
also has cases of its own that expect the very same rule to be refused,
and there the engine's native safety check answers, unaided.
"""

import re

from tiny_datalog.datalog import (
    Atom, Const, DatalogError, Literal, Program, Rule, SafetyError,
    StratificationError, Var, parse)

_TOKEN = re.compile(r'\s*(?:("(?:[^"\\]|\\.)*")|(-?\d+(?:\.\d+)?)'
                    r'|([A-Za-z_][A-Za-z0-9_]*)|(:-|.))')


class ConformanceError(Exception):
    """An engine refusal, labelled with the corpus's error vocabulary."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class SafetyViolationError(ConformanceError):
    pass


def translate_rule(text):
    """One corpus rule in our syntax (see the module docstring)."""
    out, depth, pos = [], 0, 0
    text = text.strip().rstrip(".") + "."
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if m is None or m.end() == pos:
            raise ValueError("cannot read %r at column %d" % (text, pos))
        pos = m.end()
        string, number, name, punct = m.groups()
        if string or number:
            out.append(string or number)
        elif name:
            following = text[pos:].lstrip()[:1]
            if name == "_":
                out.append("_")
            elif depth == 0 and name == "not":
                out.append("not")
            elif depth == 0 or following == "(":
                out.append("p_" + name)
            else:
                out.append("V_" + name)
        elif punct == "~" and depth == 0:
            out.append("~ ")                    # strong negation (defeasible)
        elif punct == "(" and text[pos:].lstrip()[:1] == ")":
            pos = text.index(")", pos) + 1      # Ok() is our zero-arity ok
        else:
            depth += {"(": 1, ")": -1}.get(punct, 0)
            out.append("not" if punct == "!" and depth == 0 else punct)
    return " ".join(out)


def _constant(v):
    if isinstance(v, bool):
        raise ValueError("boolean constants have no spelling here")
    if isinstance(v, (int, float)):
        return repr(v)
    return "'%s'" % v if '"' in v else '"%s"' % v


def _project_negations(rules):
    """Lesson 17's fix, applied mechanically: a negated literal whose
    variables are not all bound elsewhere becomes `not auxN(bound)`,
    with `auxN(bound) :- literal.` alongside."""
    out = []
    for rule in rules:
        body = list(rule.body)
        for i, lit in enumerate(body):
            if not lit.negated:
                continue
            elsewhere = {a.name for a in rule.head.args if isinstance(a, Var)}
            for j, other in enumerate(body):
                if j != i:
                    elsewhere |= {a.name for a in other.atom.args
                                  if isinstance(a, Var)}
            local = [a for a in lit.atom.args
                     if isinstance(a, Var) and a.name not in elsewhere]
            if not local:
                continue
            keep = []
            for a in lit.atom.args:
                if isinstance(a, Var) and a.name in elsewhere and a not in keep:
                    keep.append(a)
            aux = Atom("aux%d" % (len(out) + 1), tuple(keep))
            out.append(Rule(aux, (Literal(lit.atom, False),)))
            body[i] = Literal(aux, True)
        out.append(Rule(rule.head, tuple(body)))
    return out


def to_clauses(program, project_negations=False):
    """A corpus Program as our clauses, ready for Program(...)."""
    facts = ["p_%s(%s)." % (pred, ", ".join(_constant(v) for v in row))
             for pred, rows in program.facts.items() for row in rows]
    clauses = parse("\n".join(facts + [translate_rule(r)
                                       for r in program.rules]))
    rules = [c for c in clauses if c.body]
    if project_negations:
        rules = _project_negations(rules)
    return [c for c in clauses if not c.body] + rules


def _label(exc):
    """Name our refusal in the corpus's error vocabulary."""
    msg = str(exc)
    if isinstance(exc, StratificationError):
        return ConformanceError("cyclic_negation", msg)
    if "arity" in msg:
        return ConformanceError("arity_mismatch", msg)
    if isinstance(exc, SafetyError):
        code = ("safety_violations" if "head variable _ " in msg
                else "unbound_variable")
        return SafetyViolationError(code, msg)
    return ConformanceError("datalog_error", msg)


def corpus_name(pred):
    return pred[2:] if pred.startswith("p_") else None


class TinyDatalogEvaluator:
    """The evaluator datalog-conformance drives: evaluate() -> facts.
    `project_negations` turns on the Nemo/Souffle reading above."""

    def __init__(self, project_negations=False):
        self.project_negations = project_negations

    def program(self, corpus_program):
        try:
            return Program(to_clauses(corpus_program,
                                      self.project_negations))
        except DatalogError as exc:
            raise _label(exc) from exc

    def evaluate(self, corpus_program):
        from tiny_datalog.datalog import Engine
        engine = Engine(self.program(corpus_program))
        try:
            engine.run()
        except DatalogError as exc:
            raise _label(exc) from exc
        return {corpus_name(p): set(rows) for p, rows in engine.rels.items()
                if corpus_name(p)}


# -- defeasible theories ----------------------------------------------------
#
# The corpus reports four sections per literal; read as defeasible
# logic's proof tags (the reading SPINdle's and the papers' cases use):
#
#     definitely       +Δ
#     defeasibly       +∂
#     not_defeasibly   −∂
#     undecided        neither +∂ nor −∂
#
# Cases checked against DePYsible use the same words for DeLP's answers
# (YES / NO / UNDECIDED), a different logic: arguments compared by
# specificity.  run.py names the ones where that difference shows.

_NAMESPACE = re.compile(r"(?<=\w):(?=\w)")      # SPINdle's b:flies


def _literal(text):
    """'~flies(X)' in corpus syntax -> '~p_flies(V_X)' in ours."""
    text = _NAMESPACE.sub("__", text)
    return translate_rule(text)[:-1].replace("~ ", "~")


def theory_text(theory):
    if getattr(theory, "conflicts", None):
        raise ValueError("explicit conflict declarations are not "
                         "defeasible logic's complement-only conflicts")
    lines = []
    for pred, rows in theory.facts.items():
        neg = "~" if pred.startswith("~") else ""
        name = "p_" + _NAMESPACE.sub("__", pred.lstrip("~"))
        for row in rows:
            args = "(%s)" % ", ".join(_constant(v) for v in row) if row else ""
            lines.append("%s%s%s." % (neg, name, args))
    for arrow, rules in (("->", theory.strict_rules),
                         ("=>", theory.defeasible_rules),
                         ("~>", theory.defeaters)):
        for r in rules:
            lines.append("L_%s: %s %s %s." % (
                r.id, ", ".join(_literal(b) for b in r.body), arrow,
                _literal(r.head)))
    for a, b in theory.superiority:
        lines.append("L_%s > L_%s." % (a, b))
    return "\n".join(lines)


def _corpus_literal(lit):
    pred, args = lit
    neg = "~" if pred.startswith("~") else ""
    return neg + pred.lstrip("~")[2:].replace("__", ":"), args


SECTIONS = {"definitely": "+Δ", "defeasibly": "+∂",
            "not_defeasibly": "−∂", "undecided": "undecided"}


class TinyDatalogDefeasible:
    """Defeasible-theory evaluator for the corpus's runner."""

    def evaluate(self, theory, policy):
        from tiny_datalog.defeasible import Theory
        try:
            result = Theory.parse(theory_text(theory)).conclusions(
                policy.value)
        except DatalogError as exc:
            raise _label(exc) from exc
        out = {name: {} for name in SECTIONS}
        for name, tag in SECTIONS.items():
            for lit in result[tag]:
                pred, args = _corpus_literal(lit)
                out[name].setdefault(pred, set()).add(args)
        return out
