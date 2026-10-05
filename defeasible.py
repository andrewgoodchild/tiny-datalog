"""Launcher for defeasible logic, which lives in
tiny_datalog/defeasible.py; an install gets the
`tiny-datalog-defeasible` command instead.  Why it is three lines of
delegation that re-export only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.defeasible import main

if __name__ == "__main__":
    sys.exit(main())
