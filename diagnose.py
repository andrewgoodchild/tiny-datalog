"""Launcher for the rule debugger, which lives in
tiny_datalog/diagnose.py; an install gets the `tiny-datalog-diagnose`
command instead.  Why it is three lines of delegation that re-export
only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.diagnose import main

if __name__ == "__main__":
    sys.exit(main())
