"""Launcher for materialisation maintenance, which lives in
tiny_datalog/incremental.py; an install gets the
`tiny-datalog-incremental` command instead.  Why it is three lines of
delegation that re-export only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.incremental import main

if __name__ == "__main__":
    sys.exit(main())
