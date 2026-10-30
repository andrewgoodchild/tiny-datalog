#!/usr/bin/env python3
"""Mutation testing: how much of the code would the tests notice breaking?

Each *mutant* is the package with one small edit on one line: a
comparison flipped (< for <=), `and` for `or`, a `not` dropped, + for -,
a constant bumped by one, a condition negated, or a statement replaced
by `pass`.  The whole test suite runs against each; a mutant the suite
still passes has *survived*, and points either at a gap in the tests or
at an edit that changes nothing observable (an *equivalent* mutant,
such as a counter's starting value).  The score is the share
detected: killed by a failing test, or stopped by the time or memory
limit.

    python3 benchmarks/mutate.py --list                # mutants per module
    python3 benchmarks/mutate.py slg.py tabling.py     # run some modules
    python3 benchmarks/mutate.py -j 8 --lessons        # everything, with
                                                       # the lesson checks

Runs are slow: one full test run per mutant, about 3,300 mutants in
all, so a whole-package run takes hours even in parallel.  Each worker
gets its own copy of the repository, runs under `nice`, and is killed if
it passes the time or memory limit (a mutant can turn a loop infinite
or a set unbounded).  Results are appended to a JSON-lines file, one
mutant per line, and a rerun skips mutants already recorded there, so a
long run can be stopped and resumed.  The survivors are printed by
module and line at the end: the list to triage.
"""

import argparse
import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SWAP = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.LtE,
        ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt,
        ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot,
        ast.IsNot: ast.Is}
ARITH = {ast.Add: ast.Sub, ast.Sub: ast.Add, ast.Mult: ast.FloorDiv,
         ast.BitOr: ast.BitAnd, ast.BitAnd: ast.BitOr}
STATEMENTS = (ast.Expr, ast.Assign, ast.AugAssign, ast.Return,
              ast.Continue, ast.Break, ast.Raise)


def mutants(src):
    """Every mutant of a module's source, as (line, col, end, old, new,
    kind).  Only nodes on a single line are touched, and only their
    segment of it is rewritten, so line numbers stay put; docstrings
    are left alone."""
    tree = ast.parse(src)
    docs = set()
    for n in ast.walk(tree):
        if (isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef))
                and n.body and isinstance(n.body[0], ast.Expr)
                and isinstance(n.body[0].value, ast.Constant)
                and isinstance(n.body[0].value.value, str)):
            docs |= set(range(n.body[0].lineno, n.body[0].end_lineno + 1))
    lines = src.splitlines(keepends=True)
    out = set()

    def add(node, new, kind):
        if node.lineno == node.end_lineno and node.lineno not in docs:
            old = lines[node.lineno - 1][node.col_offset:node.end_col_offset]
            if new != old:
                out.add((node.lineno, node.col_offset, node.end_col_offset,
                         old, new, kind))

    def swapped(node, **change):
        m = copy.deepcopy(node)
        for k, v in change.items():
            setattr(m, k, v)
        return ast.unparse(m)

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for i, op in enumerate(node.ops):
                if type(op) in SWAP:
                    ops = list(node.ops)
                    ops[i] = SWAP[type(op)]()
                    add(node, swapped(node, ops=ops), "compare")
        elif isinstance(node, ast.BoolOp):
            op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            add(node, swapped(node, op=op), "boolop")
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            add(node, "(%s)" % ast.unparse(node.operand), "drop-not")
        elif isinstance(node, ast.BinOp) and type(node.op) in ARITH:
            if not (isinstance(node.left, ast.Constant)
                    and isinstance(node.left.value, str)):   # "%s" % x
                add(node, swapped(node, op=ARITH[type(node.op)]()), "arith")
        elif isinstance(node, ast.Constant) and type(node.value) is int:
            add(node, str(node.value + 1), "const")
        elif isinstance(node, ast.Constant) and type(node.value) is bool:
            add(node, str(not node.value), "const")
        elif isinstance(node, (ast.If, ast.While)):
            add(node.test, "not (%s)" % ast.unparse(node.test), "negate-cond")
        for field in ("body", "orelse", "finalbody"):
            body = getattr(node, field, None)
            for st in body if isinstance(body, list) else ():
                if isinstance(st, STATEMENTS) and not (
                        isinstance(st, ast.Expr)
                        and isinstance(st.value, ast.Constant)):
                    add(st, "pass", "delete-stmt")
    return sorted(out)


def apply(src, mutant):
    line, col, end, old, new, _kind = mutant
    lines = src.splitlines(keepends=True)
    assert lines[line - 1][col:end] == old
    lines[line - 1] = lines[line - 1][:col] + new + lines[line - 1][end:]
    return "".join(lines)


def tree_rss_kb(pgid):
    """Resident memory of a process group, children included."""
    ps = subprocess.run(["ps", "-axo", "pgid=,rss="], capture_output=True,
                        text=True).stdout
    return sum(int(rss) for g, rss in (l.split() for l in ps.splitlines())
               if int(g) == pgid)


def run_tests(workdir, lessons, time_limit, mem_limit_kb):
    """One test run, fail-fast.  Returns (status, first failure)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("TINY_DATALOG_LESSONS", None)
    if lessons:
        env["TINY_DATALOG_LESSONS"] = "1"
    proc = subprocess.Popen(
        ["nice", "-n", "19", sys.executable, "tests.py", "-f"], cwd=workdir,
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, start_new_session=True)
    err = []
    reader = threading.Thread(target=lambda: err.append(proc.stderr.read()))
    reader.start()
    start, status = time.time(), None
    while proc.poll() is None:
        time.sleep(0.5)
        if tree_rss_kb(proc.pid) > mem_limit_kb:
            status = "memory"
        elif time.time() - start > time_limit:
            status = "timeout"
        if status:
            os.killpg(proc.pid, 9)
            proc.wait()
    reader.join()
    if status:
        return status, ""
    failure = next((l for l in "".join(err).splitlines()
                    if l.startswith(("FAIL:", "ERROR:"))), "")
    return ("survived" if proc.returncode == 0 else "killed"), failure


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("modules", nargs="*",
                    help="modules of tiny_datalog/ (default: all)")
    ap.add_argument("--list", action="store_true",
                    help="count the mutants per module and stop")
    ap.add_argument("-j", "--jobs", type=int,
                    default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--lessons", action="store_true",
                    help="also run the lesson-output checks (slower; "
                         "they catch printing and counter mutants)")
    ap.add_argument("--out", default="mutation-results.jsonl")
    ap.add_argument("--time-limit", type=int, default=300, metavar="SEC")
    ap.add_argument("--mem-limit", type=int, default=1024, metavar="MB")
    args = ap.parse_args(argv)

    pkg = os.path.join(HERE, "tiny_datalog")
    names = args.modules or sorted(f for f in os.listdir(pkg)
                                   if f.endswith(".py"))
    todo = [("tiny_datalog/" + name, m) for name in names
            for m in mutants(open(os.path.join(pkg, name)).read())]
    if args.list:
        for name, n in sorted(Counter(f for f, _m in todo).items()):
            print("%-32s %5d" % (name, n))
        print("%-32s %5d" % ("total", len(todo)))
        return 0

    done = {}
    if os.path.exists(args.out):
        for line in open(args.out):
            r = json.loads(line)
            done[r["file"], tuple(r["mutant"])] = r
    todo = [(f, m) for f, m in todo if (f, m) not in done]
    print("%d mutants to run, %d already recorded in %s"
          % (len(todo), len(done), args.out))

    scratch = tempfile.mkdtemp(prefix="mutate-")
    workers = Queue()
    for i in range(args.jobs):
        d = os.path.join(scratch, str(i))
        shutil.copytree(HERE, d, ignore=shutil.ignore_patterns(
            ".git", "build", "dist", "*.egg-info", "__pycache__", "input"))
        workers.put(d)
    lock = threading.Lock()

    def one(item):
        rel, m = item
        d = workers.get()
        path = os.path.join(d, rel)
        original = open(path).read()
        try:
            open(path, "w").write(apply(original, m))
            t0 = time.time()
            status, failure = run_tests(d, args.lessons, args.time_limit,
                                        args.mem_limit * 1024)
        finally:
            open(path, "w").write(original)
            workers.put(d)
        r = {"file": rel, "mutant": list(m), "status": status,
             "killer": failure, "secs": round(time.time() - t0, 1)}
        with lock:
            with open(args.out, "a") as out:
                out.write(json.dumps(r) + "\n")
            done[rel, m] = r
            print("%-8s %s:%d  %s -> %s" % (status, rel, m[0], m[3][:40],
                                            m[4][:40]), flush=True)

    try:
        with ThreadPoolExecutor(args.jobs) as pool:
            list(pool.map(one, todo))
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    by_file = defaultdict(Counter)
    for (rel, _m), r in done.items():
        if rel[len("tiny_datalog/"):] in names:
            by_file[rel][r["status"]] += 1
    print()
    total = Counter()
    for rel, c in sorted(by_file.items()):
        total += c
        n = sum(c.values())
        print("%-32s %5d mutants, %3.0f%% detected  %s"
              % (rel, n, 100.0 * (n - c["survived"]) / n, dict(c)))
    if total:
        n = sum(total.values())
        print("%-32s %5d mutants, %3.0f%% detected"
              % ("all", n, 100.0 * (n - total["survived"]) / n))
    print("\nsurvivors:")
    for (rel, m), r in sorted(done.items()):
        if r["status"] == "survived" and rel[len("tiny_datalog/"):] in names:
            print("  %s:%d [%s] %s -> %s" % (rel, m[0], m[5], m[3], m[4]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
