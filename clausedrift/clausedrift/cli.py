"""Command line interface: ``clausedrift old.txt new.txt``."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__, compare_files
from .render import counts_table, render_json, render_markdown, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clausedrift",
        description=(
            "Explainable drift detection for AI-generated text. "
            "Compares two versions and classifies every change."
        ),
    )
    parser.add_argument("old", type=Path, help="baseline document")
    parser.add_argument("new", type=Path, help="candidate document")
    parser.add_argument(
        "-f",
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="output format (default: text)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write the report to a file instead of stdout",
    )
    parser.add_argument(
        "-t",
        "--min-similarity",
        type=float,
        default=0.5,
        metavar="0..1",
        help="similarity needed to call a replace an edit (default: 0.5)",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="include unchanged sentences in the report",
    )
    parser.add_argument(
        "--fail-over",
        type=float,
        default=None,
        metavar="SCORE",
        help="exit with status 1 when the drift score exceeds SCORE (CI gate)",
    )
    parser.add_argument(
        "--no-colour",
        "--no-color",
        dest="no_colour",
        action="store_true",
        help="disable ANSI colours",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="only print the drift score"
    )
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    for path in (args.old, args.new):
        if not path.is_file():
            print(f"clausedrift: cannot read {path}", file=sys.stderr)
            return 2

    report = compare_files(args.old, args.new, min_similarity=args.min_similarity)

    if args.quiet:
        rendered = f"{report.drift_score}"
    elif args.format == "json":
        rendered = render_json(report)
    elif args.format == "markdown":
        rendered = render_markdown(report, only_changes=not args.all)
    else:
        colour = not (args.no_colour or os.getenv("NO_COLOR") or not sys.stdout.isatty())
        rendered = render_text(report, only_changes=not args.all, colour=colour)
        rendered += f"\n\n{counts_table(report)}\n"

    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(rendered)

    if args.fail_over is not None and report.drift_score > args.fail_over:
        print(
            f"clausedrift: drift {report.drift_score} exceeds limit "
            f"{args.fail_over}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
