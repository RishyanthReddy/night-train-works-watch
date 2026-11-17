"""Local generic comparison as escaped Markdown and source-linked JSON."""

import html
import json
import re
from pathlib import Path
from urllib.parse import quote

from nightdesk.audit import append_event
from nightdesk.config import Bundle
from nightdesk.intake.mapping import digest, write_private


def escaped(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)
    # Plain Markdown text never enters an HTML attribute. Preserve apostrophes;
    # escaping them as numeric entities before escaping '#' corrupts rendering.
    text = html.escape(text, quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", text).replace("\r", " ").replace("\n", "<br>")


def _source(row):
    if row is None:
        return "—"
    ref = row["source"]
    # Absolute local path, URL-encoded so source data cannot inject Markdown links.
    url = quote(ref["url_or_path"], safe="/") + "#" + quote(ref["record_id"], safe="")
    return (f"[{escaped(ref['record_id'])}]({url}) "
            f"dataset={escaped(ref['dataset'])}, capture={escaped(ref['capture_id'])}, "
            f"sha256={ref['content_sha256']}, licence={escaped(ref['licence'])}")


def markdown(report: dict) -> str:
    lines = ["# Generic comparison", "", f"Data: {escaped(report['data_label'])}.",
             f"Bundle: {escaped(report['bundle'])}; status: {escaped(report['status'])}; "
             f"reason: {escaped(report['reason'])}; rule: {escaped(report['rule_version'])}.", "",
             "Changed between these selected files.", ""]
    for limit in report["limits"]:
        lines.append(f"- {escaped(limit)}")
    for side in ("old", "new"):
        info = report["inputs"][side]
        lines += ["", f"{side}: mode={escaped(info['mode'])}, excluded rejected rows={len({r['row'] for r in info['rejects']})}."]
        for reject in info["rejects"]:
            lines.append(f"- Rejected row {reject['row']}: field {escaped(reject['field'])}, reason {escaped(reject['reason'])}; "
                         f"source {_source({'source': reject['source']})}.")
    labels = {"changed": "Changed", "added": "Only in selected new file (added rows)",
              "unchanged": "Unchanged", "only_in_old": "Only in selected old file (meaning unknown)"}
    for group, label in labels.items():
        lines += ["", f"## {label}: {report['counts'][group]}", ""]
        for item in report[group]:
            lines += [f"### Row {escaped(item.get('key', 'identity_uncertain'))}", "",
                      f"Before source: {_source(item['old'])}", "", f"After source: {_source(item['new'])}", ""]
            for side in ("old", "new"):
                row = item[side]
                if row:
                    for name in ("fields", "extra", "unresolved"):
                        lines.append(f"{side} {name}: {escaped(row[name])}")
            for diff in item.get("field_diffs", []):
                lines.append(f"- {escaped(diff['field'])}: {escaped(diff['old'])} → {escaped(diff['new'])}")
            lines.append("")
    return "\n".join(lines) + "\n"


def export_comparison(report: dict, bundle: Bundle, out: str | Path) -> tuple[Path, Path]:
    if report["bundle"] != bundle.name:
        raise ValueError("report belongs to another bundle")
    folder = bundle.resolve(out)
    # A separate immutable export directory avoids partial overwrites and preserves history.
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    rendered = markdown(report)
    # Address the pair by both formats, so a rendering fix preserves old exports.
    stem = "comparison-" + digest(text.encode() + b"\0" + rendered.encode())
    folder.mkdir(parents=True, exist_ok=True)
    paths = (folder / f"{stem}.md", folder / f"{stem}.json")
    for path, contents in zip(paths, (rendered, text)):
        bundle.resolve(path)
        if path.is_symlink():
            raise ValueError("export target is a symlink")
        if path.exists():
            if path.read_text("utf-8") != contents:
                raise ValueError("existing export differs; refusing to overwrite")
        else:
            write_private(path, contents)
    append_event(bundle, "comparison_exported", {"rule_version": report["rule_version"],
                                              "status": report["status"], "counts": report["counts"],
                                              "json_sha256": digest(text.encode()),
                                              "paths": [str(p) for p in paths]})
    return paths
