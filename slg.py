"""Launcher for top-down evaluation with SLG resolution, which lives in
tiny_datalog/slg.py; an install gets the `tiny-datalog-slg`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.slg import main

if __name__ == "__main__":
    sys.exit(main())
