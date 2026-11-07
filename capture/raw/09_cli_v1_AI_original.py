"""Command-line interface for the NetArchitect network planning tool."""

import argparse
import sys
from pathlib import Path

from engine.errors import NetArchitectError
from engine.media import select_media
from engine.params import load_custom, load_preset
from engine.planner import build_plan, render_report


PRESET_NAMES = ("campus_lan", "metro_man", "global_wan")


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser and configure CLI subcommands."""
    parser = argparse.ArgumentParser(
        prog="NetArchitect",
        description="Enterprise network architecture planning and recommendations.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    # List available presets.
    subparsers.add_parser(
        "list",
        help="List available network configuration presets.",
    )

    # Generate a complete network architecture plan.
    plan_parser = subparsers.add_parser(
        "plan",
        help="Build and display a network architecture plan.",
    )

    source_group = plan_parser.add_mutually_exclusive_group(required=True)

    source_group.add_argument(
        "--preset",
        choices=PRESET_NAMES,
        metavar="NAME",
        help="Load a predefined network configuration.",
    )

    source_group.add_argument(
        "--custom",
        metavar="FILE",
        help="Load a custom JSON network configuration.",
    )

    plan_parser.add_argument(
        "--out",
        metavar="FILE",
        help="Also save the generated report to a file.",
    )

    # Check physical media suitability for a link.
    link_parser = subparsers.add_parser(
        "check-link",
        help="Recommend a physical transmission medium for a link.",
    )

    link_parser.add_argument(
        "--distance",
        type=float,
        required=True,
        metavar="FLOAT",
        help="Physical link distance in metres.",
    )

    link_parser.add_argument(
        "--media",
        type=str,
        default=None,
        metavar="TEXT",
        help="Optional requested transmission medium.",
    )

    return parser


def _handle_list() -> int:
    """Print the names of all available presets."""
    for preset in PRESET_NAMES:
        print(preset)

    return 0


def _handle_plan(args: argparse.Namespace) -> int:
    """Build, display, and optionally save a network architecture report."""
    if args.preset is not None:
        params = load_preset(args.preset)
    else:
        params = load_custom(args.custom)

    plan = build_plan(params)
    report = render_report(plan)

    print(report)

    if args.out is not None:
        output_path = Path(args.out).expanduser()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")

        print(f"Report written to {args.out}")

    return 0


def _handle_check_link(args: argparse.Namespace) -> int:
    """Evaluate a physical link and print its media recommendation."""
    decision = select_media(
        distance_m=args.distance,
        requested_media=args.media,
    )

    references = ", ".join(decision.references)

    print(f"Choice: {decision.choice}")
    print(f"Justification: {decision.justification}")
    print(f"References: {references}")

    return 0


def main(argv: list[str] | None = None) -> int:
    """Execute the requested NetArchitect CLI command.

    Args:
        argv: Optional command-line argument list. Uses system arguments
            when None.

    Returns:
        Exit code 0 on success or 2 when a project error occurs.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            return _handle_list()

        if args.command == "plan":
            return _handle_plan(args)

        if args.command == "check-link":
            return _handle_check_link(args)

        parser.error(f"Unknown command: {args.command}")

    except NetArchitectError as exc:
        print(
            f"ERROR ({type(exc).__name__}): {exc}",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
