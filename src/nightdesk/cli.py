"""nightdesk command-line entry point (argparse). Subcommands are added per task."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from nightdesk.intake.sniff import format_profile, profile
from nightdesk.intake.table import FILE_TYPES, TableError, read_table
from nightdesk.config import get_bundle, selected_bundle_name
from nightdesk.intake.mapping import captures, confirm_mapping, ingest, check_input
from nightdesk.intake.flatten import flatten, write_flat


def _cmd_sniff(args: argparse.Namespace) -> int:
    try:
        table = read_table(
            args.file,
            args.type,
            encoding=args.encoding,
            delimiter=args.delimiter,
            sheet=args.sheet,
            header_row=args.header_row,
            records_path=args.records_path,
        )
    except TableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    prof = profile(table)
    if args.json:
        print(json.dumps(prof, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_profile(prof))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nightdesk",
        description=(
            "Evidence-linked intake and comparison tools. Data is scoped to one "
            "bundle (practice, es, or test-<slug>) under data/out/<bundle>/."
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    sniff = sub.add_parser(
        "sniff",
        help="profile a CSV/XLSX/JSON file: columns, types, null rates, samples",
        description="Profile a file without changing it. Prints to stdout; writes nothing.",
    )
    sniff.add_argument("file")
    sniff.add_argument("--type", choices=FILE_TYPES, help="file type (default: from the suffix)")
    sniff.add_argument("--encoding", default="utf-8-sig", help="CSV/JSON text encoding (default: utf-8-sig)")
    sniff.add_argument("--delimiter", default=",", help="CSV delimiter (default: ,)")
    sniff.add_argument("--sheet", help="XLSX sheet name (default: first sheet)")
    sniff.add_argument("--header-row", type=int, default=1, help="CSV/XLSX 1-based header row (default: 1)")
    sniff.add_argument("--records-path", help="JSON dotted path to the list of records, e.g. data.items")
    sniff.add_argument("--json", action="store_true", help="print the profile as JSON")
    sniff.set_defaults(func=_cmd_sniff)

    mapping = sub.add_parser("mapping", help="confirm a mapping's current hash")
    mapping_sub = mapping.add_subparsers(dest="action", required=True)
    confirm = mapping_sub.add_parser("confirm")
    confirm.add_argument("yaml")
    confirm.add_argument("--bundle", default=None)
    confirm.add_argument("--actor", help="person confirming (default: local username)")
    confirm.set_defaults(func=_cmd_confirm)

    intake = sub.add_parser("ingest", help="apply a confirmed GenericRow mapping")
    intake.add_argument("file")
    intake.add_argument("--mapping", required=True)
    intake.add_argument("--bundle", default=None)
    intake.set_defaults(func=_cmd_ingest)

    rejects = sub.add_parser("rejects", help="list rejected rows in this bundle")
    rejects.add_argument("--bundle", default=None)
    rejects.set_defaults(func=_cmd_rejects)

    flat = sub.add_parser("flatten", help="join header rows into a new CSV (stdout by default)")
    flat.add_argument("file")
    flat.add_argument("--header-rows", type=int, required=True)
    flat.add_argument("--sheet")
    flat.add_argument("--delimiter", default=",")
    flat.add_argument("--encoding", default="utf-8-sig")
    flat.add_argument("--out")
    flat.add_argument("--bundle", default=None)
    flat.set_defaults(func=_cmd_flatten)

    compare = sub.add_parser("compare", help="compare selected tables and export locally")
    compare.add_argument("old")
    compare.add_argument("new")
    compare.add_argument("--key")
    compare.add_argument("--bundle", default=None)
    compare.add_argument("--out")
    compare.add_argument("--old-capture")
    compare.add_argument("--new-capture")
    compare.set_defaults(func=_cmd_compare)
    return parser


def _bundle(args):
    return get_bundle(args.bundle or selected_bundle_name())


def _cmd_confirm(args):
    sha = confirm_mapping(args.yaml, _bundle(args), args.actor)
    print(f"confirmed {sha} bundle={_bundle(args).name}")
    return 0


def _cmd_ingest(args):
    result = ingest(args.file, args.mapping, _bundle(args))
    print(f"accepted={result['accepted']} rejected={result['rejected']} filtered={result['filtered']} "
          f"licence={result['licence']} capture={result['capture_id']}")
    return 0


def _cmd_rejects(args):
    count = 0
    for capture in captures(_bundle(args)):
        for item in capture["rejects"]:
            count += 1
            print(f"{item['source']['url_or_path']} row={item['row']} field={item['field']} "
                  f"reason={item['reason']} capture={capture['capture'].capture_id}")
    if not count:
        print("no rejects")
    return 0


def _cmd_flatten(args):
    options = dict(header_rows=args.header_rows, sheet=args.sheet, delimiter=args.delimiter, encoding=args.encoding)
    bundle = _bundle(args)
    check_input(args.file, bundle)
    if args.out:
        write_flat(args.file, args.out, bundle=bundle, **options)
        print(f"flattened to {args.out}; source unchanged")
    else:
        print(flatten(args.file, **options), end="")
    return 0


def _cmd_compare(args):
    from nightdesk.generic import compare_files
    from nightdesk.export import export_comparison
    bundle = _bundle(args)
    report = compare_files(args.old, args.new, bundle, args.key,
                           old_capture=args.old_capture, new_capture=args.new_capture)
    paths = export_comparison(report, bundle, args.out or bundle.root)
    counts = " ".join(f"{k}={v}" for k, v in report["counts"].items())
    print(f"status={report['status']} reason={report['reason']} data={report['data_label']} {counts}")
    print("Rows absent from a selected file have unknown meaning; rejected rows are excluded.")
    for path in paths:
        print(path)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except (ValueError, OSError, LookupError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
