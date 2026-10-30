"""A small self-contained demo.

Run it with::

    python examples/demo.py

It compares two versions of a generated product description, prints a colour
report, and shows how to gate a pipeline on the drift score.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from clausedrift import compare  # noqa: E402
from clausedrift.render import render_markdown, render_text  # noqa: E402

BEFORE = """
The Aurora Desk Lamp is a compact LED lamp for small workspaces.

It provides 400 lumens of warm white light at 2700K.

The lamp has a brushed aluminium body and a weighted base.

It ships with a 2 metre braided USB-C cable.

The warranty period is 12 months from the date of purchase.
"""

AFTER = """
The Aurora Desk Lamp is a compact LED lamp designed for small workspaces.

It provides 500 lumens of warm white light at 3000K.

The lamp has a brushed aluminium body and a weighted base.

It ships with a 2 metre braided USB-C cable and a spare bulb.

The warranty period is 24 months from the date of purchase.
"""


def main() -> int:
    report = compare(BEFORE, AFTER)
    report.source_old = "description_v1"
    report.source_new = "description_v2"

    print(render_text(report, colour=False))
    print()

    # A pipeline gate: fail if the new prompt version drifted more than 15/100.
    threshold = 15.0
    if report.drift_score > threshold:
        print(f"GATE FAILED: drift {report.drift_score} > {threshold}")
        Path("demo_report.md").write_text(render_markdown(report), encoding="utf-8")
        print("wrote demo_report.md")
        return 1

    print(f"GATE PASSED: drift {report.drift_score} <= {threshold}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
