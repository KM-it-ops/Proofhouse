#!/usr/bin/env python3
"""Run the packaged reference workflow.

``--cli`` selects the console script. With no ``--cli``, this interpreter's
``python -m proofhouse.compiler.cli_compiler`` is used. ``proofhouse-compiler demo``
is the same run without ``--cli``.
"""

from proofhouse.optimize.reference_workflow import main

if __name__ == "__main__":
    raise SystemExit(main())
