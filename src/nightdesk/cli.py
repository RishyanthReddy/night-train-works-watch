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


def _cmd_gtfs(args):
    from datetime import date
    from nightdesk.adapters.gtfs import import_gtfs
    result = import_gtfs(args.file, get_bundle(args.bundle or selected_bundle_name()), actor=args.actor,
        namespace=args.namespace, licence=args.licence,
        dates=[date.fromisoformat(d) for d in args.service_date] if args.service_date else None,
        trip_ids=args.trip_id)
    print(f"GTFS scheduled only: accepted={result['accepted']} rejected={result['rejected']} capture={result['capture_id']}; path_unresolved, never a booked path")
    return 0


def _cmd_aliases(args):
    from nightdesk.stations import import_aliases
    identifier = import_aliases(args.file, get_bundle(args.bundle or selected_bundle_name()), args.actor)
    print("confirmed alias table=" + identifier)
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

    batch = sub.add_parser("capture", help="confirm or import a declared multi-file capture")
    actions = batch.add_subparsers(dest="action", required=True)
    for action in ("confirm", "import"):
        cmd = actions.add_parser(action)
        cmd.add_argument("manifest")
        cmd.add_argument("--bundle", default=None)
        if action == "confirm":
            cmd.add_argument("--actor", required=True)
        cmd.set_defaults(func=_cmd_capture)

    gtfs = sub.add_parser("gtfs", help="import a local GTFS schedule as unresolved-path scheduled runs")
    gtfs_sub = gtfs.add_subparsers(dest="action", required=True)
    gtfs_import = gtfs_sub.add_parser("import")
    gtfs_import.add_argument("file")
    gtfs_import.add_argument("--bundle", default=None)
    gtfs_import.add_argument("--actor", required=True)
    gtfs_import.add_argument("--namespace", required=True)
    gtfs_import.add_argument("--licence", required=True)
    gtfs_import.add_argument("--service-date", action="append")
    gtfs_import.add_argument("--trip-id", action="append")
    gtfs_import.set_defaults(func=_cmd_gtfs)

    aliases = sub.add_parser("aliases", help="import reviewed sourced station aliases into one bundle")
    alias_sub = aliases.add_subparsers(dest="action", required=True)
    alias_import = alias_sub.add_parser("import")
    alias_import.add_argument("file")
    alias_import.add_argument("--bundle", default=None)
    alias_import.add_argument("--actor", required=True)
    alias_import.set_defaults(func=_cmd_aliases)

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
    links = sub.add_parser("links", help="import a crosswalk or explicitly confirm journey members")
    actions = links.add_subparsers(dest="action", required=True)
    imp = actions.add_parser("import")
    imp.add_argument("capture")
    imp.add_argument("--bundle", default=None)
    imp.set_defaults(func=_cmd_links)
    conf = actions.add_parser("confirm")
    conf.add_argument("journey")
    conf.add_argument("--revision", action="append", required=True)
    conf.add_argument("--actor", required=True)
    conf.add_argument("--service-date-rule", required=True, help="explicit ISO service date or * for same-date rule")
    conf.add_argument("--bundle", default=None)
    conf.set_defaults(func=_cmd_links)
    show = actions.add_parser("list")
    show.add_argument("--bundle", default=None)
    show.set_defaults(func=_cmd_links)
    review = sub.add_parser("review", help="record a local decision bound to a revision")
    review.add_argument("revision")
    review.add_argument("--actor", required=True)
    review.add_argument("--disposition", choices=["accepted_locally", "needs_clarification", "rejected_locally"], required=True)
    review.add_argument("--reason", required=True)
    review.add_argument("--owner")
    review.add_argument("--question")
    review.add_argument("--bundle", default=None)
    review.set_defaults(func=_cmd_review)
    demo = sub.add_parser("demo", help="verify public demo assets and their input references")
    actions = demo.add_subparsers(dest="action", required=True)
    check = actions.add_parser("check")
    check.add_argument("--manifest", default="mappings/demo.yaml")
    check.add_argument("--bundle", default=None)
    check.set_defaults(func=_cmd_demo)
    consent = sub.add_parser("consent", help="record explicit bundle consent to Mistral only")
    consent.add_argument("--bundle", default=None)
    consent.add_argument("--actor", required=True)
    toggle = consent.add_mutually_exclusive_group(required=True)
    toggle.add_argument("--allow", choices=["mistral"])
    toggle.add_argument("--revoke", choices=["mistral"])
    consent.set_defaults(func=_cmd_consent)
    text = sub.add_parser("text", help="quoted work proposal or local manual import")
    actions = text.add_subparsers(dest="action", required=True)
    for action in ("propose", "import"):
        cmd = actions.add_parser(action)
        cmd.add_argument("file")
        cmd.add_argument("--mapping", required=True)
        cmd.add_argument("--bundle", default=None)
        if action == "propose":
            cmd.add_argument("--provider", choices=["off", "replay", "mistral"], default="off")
            cmd.add_argument("--replay")
        else:
            cmd.add_argument("--proposal", required=True)
            cmd.add_argument("--drafted-by", choices=["manual","llm","replay"], default="manual")
            cmd.add_argument("--actor", required=True)
        cmd.set_defaults(func=_cmd_text)
    audit = sub.add_parser("audit", help="check a hash chain or print an external seal")
    actions = audit.add_subparsers(dest="action", required=True)
    for action in ("verify", "seal", "upgrade"):
        cmd = actions.add_parser(action)
        cmd.add_argument("--bundle", default=None)
        if action == "verify":
            cmd.add_argument("--seal")
            cmd.add_argument("--file", help="read-only audit copy inside this bundle; requires trusted seal/count")
            cmd.add_argument("--count", type=int)
        if action == "upgrade":
            cmd.add_argument("--actor", required=True)
        cmd.set_defaults(func=_cmd_audit)
    return parser


def _bundle(args):
    return get_bundle(args.bundle or selected_bundle_name())


def _cmd_demo(args):
    from nightdesk.demo import check_demo
    registry = check_demo(args.manifest, get_bundle(args.bundle) if args.bundle else None)
    print(f"demo check passed: {len(registry.assets)} hashed CC0/synthetic assets; input references checked; no network")
    return 0


def _cmd_consent(args):
    from nightdesk.llm.client import consent
    consent(_bundle(args), args.actor, allow=bool(args.allow))
    print("Mistral consent recorded locally: " + ("allowed" if args.allow else "revoked"))
    return 0


def _cmd_text(args):
    from pathlib import Path
    from nightdesk.llm.client import propose
    from nightdesk.intake.text import submit_text
    bundle = _bundle(args)
    check_input(args.file, bundle)
    text = Path(args.file).read_text("utf-8")
    if args.action == "propose":
        result = propose(bundle, text, args.mapping, provider=args.provider, replay_path=args.replay)
    else:
        check_input(args.proposal, bundle)
        result = submit_text(bundle, text, json.loads(Path(args.proposal).read_text()), args.mapping, actor=args.actor, mode=args.drafted_by)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 1 if result.get("rejected") or result.get("accepted") is False else 0


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


def _cmd_capture(args):
    from nightdesk.intake.batch import confirm_batch, ingest_batch
    bundle = _bundle(args)
    if args.action == "confirm":
        print("confirmed capture mappings: " + ", ".join(confirm_batch(args.manifest, bundle, args.actor)))
    else:
        result = ingest_batch(args.manifest, bundle)
        from nightdesk.links import import_links
        from nightdesk.desk import snapshot
        for identifier in result["children"].values():
            if snapshot(bundle, identifier)["metadata"]["record_type"] == "JourneyLinkMember":
                import_links(bundle, identifier)
        print(f"capture={result['capture'].capture_id} complete={result['capture'].complete} rejected={len(result['rejects'])} label={result['metadata']['label']}")
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


def _cmd_links(args):
    from nightdesk.links import import_links, confirm_link, links
    bundle = _bundle(args)
    if args.action == "import":
        print("recorded source links: " + ", ".join(import_links(bundle, args.capture)))
    elif args.action == "confirm":
        print("confirmed human link: " + confirm_link(bundle, args.journey, args.revision, args.actor, args.service_date_rule))
    else:
        print(json.dumps([link.model_dump(mode="json") for link in links(bundle)], ensure_ascii=False, indent=2))
    return 0


def _cmd_review(args):
    from nightdesk.review import record_decision, follow_up
    if bool(args.owner) != bool(args.question):
        raise ValueError("follow-up requires both --owner and --question")
    bundle = _bundle(args)
    decision = record_decision(bundle, args.revision, args.actor, args.disposition, args.reason)
    print(decision.model_dump_json())
    if args.owner:
        print(follow_up(bundle, args.revision, args.owner, args.question).model_dump_json())
    return 0


def _cmd_audit(args):
    from nightdesk.audit import verify, upgrade_legacy
    bundle = _bundle(args)
    if args.action == "upgrade":
        result = upgrade_legacy(bundle, args.actor)
    elif args.action == "verify":
        result = verify(bundle, seal=args.seal, count=args.count, copy_path=args.file)
    else:
        result = verify(bundle)
        print("Keep this hash and count outside the audit log; source truth is not proved.")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
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
