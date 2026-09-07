"""Launcher for KL-ONE style classification, which lives in
tiny_datalog/subsumption.py.

This file is deliberately three lines of delegation.  It sits at the
repo root so the lessons' `python3 subsumption.py ...` commands run
straight from a checkout with nothing installed, and it is left out of
the built package — an install gets the `tiny-datalog-subsumption`
command instead.

It re-exports nothing but `main`, on purpose.  Were it to re-export the
AST classes too, `import subsumption` and `import
tiny_datalog.subsumption` would hand back two different module objects,
and isinstance checks across them would quietly fail — the double-import
trap that this layout exists to close.
"""

import sys

from tiny_datalog.subsumption import main

if __name__ == "__main__":
    sys.exit(main())
