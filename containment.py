"""Launcher for query containment, which lives in
tiny_datalog/containment.py; an install gets the
`tiny-datalog-containment` command instead.  Why it is three lines of
delegation that re-export only `main`: see the root datalog.py.
"""

import sys

from tiny_datalog.containment import main

if __name__ == "__main__":
    sys.exit(main())
