"""Mapping v1 scalar intake. YAML is data; parsers are a fixed allowlist.

Phase 0 artifacts live under the bundle root. Typed revisions/store are Phase 1.
"""

from __future__ import annotations

import copy
import getpass
import hashlib
import json
import math
import re
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from nightdesk.audit import append_event, append_events, canonical_json, read_events
from nightdesk.config import Bundle, BundleError, OUT_ROOT, ES_INPUT_ROOT, is_within, MAX_NUMBER_TEXT, MAX_NUMBER_EXPONENT
from nightdesk.gates import common_gates
from nightdesk.intake.table import Table, TableError, read_table
from nightdesk.model import Capture, GenericRow, JSONValue, SourceRef


class MappingError(ValueError):
    """Invalid mapping, unconfirmed hash, or invalid stored capture."""


class _Config(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class FileSpec(_Config):
    type: Literal["csv", "xlsx", "json"]
    encoding: str = "utf-8-sig"
    delimiter: str = Field(default=",", min_length=1, max_length=1)
    sheet: str | None = None
    records_path: str | None = None


class FieldSpec(_Config):
    column: str | None = None
    parse: str = "str"
    prefix: str = ""
    default: JSONValue = None
    date_format: str | None = None
    time_format: str | None = None


class Mapping(_Config):
    version: Literal[1]
    dataset: str = Field(min_length=1)
    licence: str = Field(min_length=1)
    external_processing_allowed: bool = False
    file: FileSpec
    header_row: int = Field(default=1, ge=1)
    timezone: str | None = None
    record: Literal["GenericRow"]
    required: list[str] = Field(default_factory=list)
    null_tokens: list[JSONValue] = Field(default_factory=lambda: ["", "NULL"])
    filter: dict[str, JSONValue] = Field(default_factory=dict)
    complete: bool = False
    fields: dict[str, FieldSpec] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def integer_version(cls, values):
        if isinstance(values, dict) and type(values.get("version")) is not int:
            raise ValueError("version must be integer 1")
        return values

    @model_validator(mode="after")
    def check_contract(self):
        if self.timezone:
            ZoneInfo(self.timezone)
        if any(n not in self.fields for n in self.required):
            raise ValueError("required fields must be named in fields")
        if any(not n or "." in n for n in self.fields):
            raise ValueError("destination fields must be nonempty scalar names; dotted targets are Phase 1")
        for spec in self.fields.values():
            columns_for(spec)
            kind = spec.parse.split(":", 1)[0]
            if kind in {"date", "time", "datetime"} and not spec.parse.partition(":")[2]:
                raise ValueError("date/time/datetime parser needs a strptime format")
            if kind in {"time", "datetime", "date_time"} and not self.timezone:
                raise ValueError("time parsers require a declared timezone")
            if kind == "enum":
                enum_values(spec)
            if spec.prefix and kind != "str":
                raise ValueError("prefix is supported only for str parsers")
        return self


class UniqueSafeLoader(yaml.SafeLoader):
    """Reject duplicate keys rather than letting the last silently win."""


def _unique_object(loader, node):
    result = {}
    for k, v in node.value:
        key = loader.construct_object(k)
        if not isinstance(key, (str, int, float, bool, type(None))) or key in result:
            raise MappingError("YAML has a duplicate or invalid key")
        result[key] = loader.construct_object(v)
    return result


UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_object)


def safe_yaml(raw: str):
    # Anchors/aliases/merges are unnecessary in v1 and can hide huge recursive values.
    for token in yaml.scan(raw):
        if isinstance(token, (yaml.tokens.AnchorToken, yaml.tokens.AliasToken)):
            raise MappingError("YAML anchors and aliases are not supported")
    return yaml.load(raw, Loader=UniqueSafeLoader)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_mapping(path: str | Path) -> tuple[Mapping, str]:
    raw = Path(path).read_bytes()
    try:
        mapping = Mapping.model_validate(safe_yaml(raw.decode("utf-8")))
    except (ValueError, yaml.YAMLError, ZoneInfoNotFoundError, TypeError, RecursionError) as exc:
        raise MappingError(f"invalid mapping {path}: {exc}") from exc
    return mapping, digest(raw)


SCALAR_PARSERS = {"str", "int", "float", "seconds", "minutes_to_seconds", "date", "time", "datetime", "date_time", "enum"}


def columns_for(spec: FieldSpec) -> list[str]:
    kind, sep, arg = spec.parse.partition(":")
    if kind not in SCALAR_PARSERS or (kind in {"str", "int", "float", "seconds", "minutes_to_seconds"} and sep):
        raise ValueError(f"parser {spec.parse!r} is not in the scalar allowlist")
    if kind == "date_time":
        cols = safe_yaml(arg)
        if not isinstance(cols, list) or len(cols) != 2 or not all(isinstance(c, str) and c for c in cols):
            raise ValueError("date_time needs [date column, time column]")
        if not spec.date_format or not spec.time_format:
            raise ValueError("date_time needs date_format and time_format")
        if spec.column is not None:
            raise ValueError("date_time uses two columns, not column")
        return cols
    if not spec.column:
        raise ValueError("each scalar field needs column")
    return [spec.column]


def enum_values(spec: FieldSpec) -> dict:
    values = safe_yaml(spec.parse.partition(":")[2])
    if not isinstance(values, dict) or not values or not all(isinstance(v, str) for v in values.values()):
        raise ValueError("enum requires a nonempty raw-to-canonical string map")
    if spec.default not in (None, "other", "unknown"):
        raise ValueError("unknown enum default must be other or unknown")
    return values


def _cell(row: dict, name: str):
    # A literal header containing a dot takes precedence over a JSON dotted path.
    if name in row:
        return row[name]
    value = row
    for part in name.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(name)
        value = value[part]
    return value


def _remove(extra: dict, name: str):
    if name in extra:
        extra.pop(name)
        return
    parts = name.split(".")
    node = extra
    parents = []
    for part in parts[:-1]:
        if part not in node or not isinstance(node[part], dict):
            return
        parents.append((node, part))
        node = node[part]
    node.pop(parts[-1], None)
    for parent, part in reversed(parents):
        if not parent[part]:
            parent.pop(part)


def json_value(value):
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_value(v) for v in value]
    return value


def _aware(value: datetime, zone: str) -> tuple[str | None, str | None]:
    if value.tzinfo is not None:
        return value.isoformat(), None
    tz = ZoneInfo(zone)
    a, b = (value.replace(tzinfo=tz, fold=fold) for fold in (0, 1))
    if a.utcoffset() != b.utcoffset() or a.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != value:
        return None, "ambiguous_local_time"
    return a.isoformat(), None


def parse_value(value, spec: FieldSpec, zone: str | None):
    kind, _, fmt = spec.parse.partition(":")
    if kind == "str":
        if isinstance(value, (dict, list)):
            raise ValueError("scalar_expected")
        return spec.prefix + str(value), None
    if kind in {"int", "seconds", "minutes_to_seconds", "float"}:
        if isinstance(value, bool):
            raise ValueError("invalid_number")
        text = str(value)
        if len(text) > MAX_NUMBER_TEXT:
            raise ValueError("number_out_of_range")
        try:
            number = Decimal(text)
        except InvalidOperation:
            raise ValueError("invalid_number") from None
        if not number.is_finite():
            raise ValueError("non_finite_number")
        if abs(number.adjusted()) > MAX_NUMBER_EXPONENT:
            raise ValueError("number_out_of_range")
        if kind == "float":
            f = float(number)
            if not math.isfinite(f):
                raise ValueError("non_finite_number")
            if f == 0.0 and number != 0:
                raise ValueError("number_out_of_range")
            return f, None
        if kind == "minutes_to_seconds":
            number *= 60
        if number != number.to_integral_value():
            raise ValueError("integer_seconds_required" if kind != "int" else "integer_required")
        return int(number), None
    if kind == "enum":
        values = enum_values(spec)
        if value in values:
            return values[value], None
        return spec.default or "unknown", "unknown_enum"
    if kind == "date_time":
        parsed = datetime.strptime(value, f"{spec.date_format} {spec.time_format}")
        return _aware(parsed, zone)
    if kind in {"date", "time", "datetime"}:
        # XLSX may already hold a typed date/time; strptime remains the declared contract.
        if isinstance(value, datetime):
            parsed = value
        elif kind == "date" and isinstance(value, date):
            return value.isoformat(), None
        elif kind == "time" and isinstance(value, time):
            return value.isoformat(), None
        else:
            parsed = datetime.strptime(str(value), fmt)
        if kind == "date":
            return parsed.date().isoformat(), None
        if kind == "time":
            return parsed.timetz().isoformat(), None
        return _aware(parsed, zone)
    raise ValueError("unsupported_parser")


def confirm_mapping(path: str | Path, bundle: Bundle, actor: str | None = None) -> str:
    check_input(path, bundle)
    _, sha = load_mapping(path)
    actor = actor or getpass.getuser()
    if not actor.strip():
        raise MappingError("confirmation requires an actor")
    append_event(bundle, "mapping_confirmed", {"mapping_sha256": sha, "path": str(Path(path).resolve()), "actor": actor})
    return sha


def check_input(path: str | Path, bundle: Bundle):
    """Explicit files are allowed, but known operational bundle roots cannot cross."""
    target = Path(path).resolve()
    out = OUT_ROOT.resolve()
    if is_within(target, out) and not is_within(target, bundle.real_root()):
        raise BundleError("input belongs to another bundle")
    es = ES_INPUT_ROOT.resolve()
    if is_within(target, es) and bundle.name != "es":
        raise BundleError("data/es input requires the es bundle")


def _confirmed(bundle: Bundle, sha: str) -> bool:
    return any(e.kind == "mapping_confirmed" and e.payload.get("mapping_sha256") == sha for e in read_events(bundle))


def read_mapped_table(path, mapping: Mapping) -> Table:
    options = mapping.file.model_dump()
    return read_table(path, options.pop("type"), **options, header_row=mapping.header_row)


def map_table(table: Table, mapping: Mapping, bundle: Bundle, capture_id: str, captured_at: datetime):
    accepted, rejects, filtered = [], [], []
    used = {c for spec in mapping.fields.values() for c in columns_for(spec)}
    missing_columns = {c for c in used if c not in table.columns and c.split(".")[0] not in table.columns}
    for raw, number in zip(table.rows, table.row_numbers):
        ref = SourceRef(bundle=bundle.name, dataset=mapping.dataset, record_id=f"row:{number}",
                        capture_id=capture_id, content_sha256=digest(canonical_json(json_value(raw)).encode()),
                        captured_at=captured_at, url_or_path=str(table.path.resolve()), licence=mapping.licence)
        source = ref.model_dump(mode="json")
        try:
            if any(_cell(raw, col) != val for col, val in mapping.filter.items()):
                filtered.append({"source": source, "reason": "filter_not_equal"})
                continue
        except KeyError as exc:
            raise MappingError(f"filter column {exc.args[0]!r} not found") from None
        fields, unresolved, failures = {}, {}, []
        for name, spec in mapping.fields.items():
            columns = columns_for(spec)
            try:
                cells = []
                for column in columns:
                    if column in missing_columns:
                        raise KeyError(column)
                    try:
                        cells.append(_cell(raw, column))
                    except KeyError:
                        if table.file_type != "json":
                            raise
                        cells.append(None)
                is_missing = any(c is None or c in mapping.null_tokens for c in cells)
                if is_missing:
                    if spec.parse.split(":")[0] in {"time", "datetime", "date_time"}:
                        fields[name] = None
                        unresolved[name] = {"reason": "missing_time", "raw": json_value(cells), "timezone": mapping.timezone}
                    elif spec.default is None:
                        fields[name] = None
                    else:
                        fields[name], reason = parse_value(spec.default, spec, mapping.timezone)
                        if reason:
                            unresolved[name] = {"reason": reason, "raw": json_value(cells), "default": spec.default,
                                                "timezone": mapping.timezone}
                else:
                    value = " ".join(str(c) for c in cells) if spec.parse.startswith("date_time:") else cells[0]
                    fields[name], reason = parse_value(value, spec, mapping.timezone)
                    if reason:
                        unresolved[name] = {"reason": reason, "raw": json_value(cells), "timezone": mapping.timezone}
                empty = fields[name] is None or (isinstance(fields[name], str) and not fields[name].strip())
                if name in mapping.required and empty and name not in unresolved:
                    raise ValueError("required_missing")
            except (ValueError, TypeError, KeyError, OverflowError) as exc:
                kind = spec.parse.split(":")[0]
                code = str(exc)
                # Raw source values from strptime exceptions must never enter the audit log.
                known = {"required_missing", "invalid_number", "non_finite_number", "integer_seconds_required",
                         "integer_required", "scalar_expected", "number_out_of_range"}
                reason = "column_missing" if isinstance(exc, KeyError) else (code if code in known else f"invalid_{kind}")
                failures.append({"row": number, "field": name, "reason": reason,
                                 "gate": "C4" if spec.parse.split(":")[0] in {"date", "time", "datetime", "date_time"} else "C1", "source": source})
        extra = copy.deepcopy(raw)
        for col in used:
            _remove(extra, col)
        if not failures:
            try:
                record = GenericRow(source=ref, fields=fields, extra=json_value(extra), unresolved=unresolved)
                for gate in common_gates(record):
                    if not gate.passed:
                        failures.append({"row": number, "field": gate.detail, "reason": gate.reason_code, "gate": gate.gate, "source": source})
            except ValidationError:
                failures.append({"row": number, "field": "record", "reason": "schema_invalid", "gate": "C1", "source": source})
        if failures:
            rejects.extend(failures)
        else:
            accepted.append(record)
    return accepted, rejects, filtered


def write_private(path: Path, text: str, *, exclusive: bool = True):
    """Never follow a pre-existing artifact symlink or overwrite a prior capture."""
    import os
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)


def ingest(path: str | Path, mapping_path: str | Path, bundle: Bundle) -> dict:
    check_input(path, bundle)
    check_input(mapping_path, bundle)
    mapping, sha = load_mapping(mapping_path)
    if not _confirmed(bundle, sha):
        append_event(bundle, "ingest_refused", {"reason": "mapping_not_confirmed", "mapping_sha256": sha})
        raise MappingError("mapping_not_confirmed: confirm this mapping's current hash in this bundle first")
    path = Path(path)
    file_sha = digest(path.read_bytes())
    capture_id = digest(canonical_json([bundle.name, str(path.resolve()), file_sha, sha]).encode())
    folder = bundle.resolve(bundle.root / "captures" / capture_id)
    if folder.exists():
        return load_capture(folder, bundle)["metadata"] | {"reused": True}
    table = read_mapped_table(path, mapping)
    if digest(path.read_bytes()) != file_sha:
        raise MappingError("input changed while reading; retry")
    now = datetime.now(timezone.utc)
    rows, rejects, filtered = map_table(table, mapping, bundle, capture_id, now)
    incomplete = [] if mapping.complete else ["not_declared_complete"]
    if rejects:
        incomplete.append("rejected_rows")
    if any(r.unresolved for r in rows):
        incomplete.append("unresolved_fields")
    capture = Capture(capture_id=capture_id, bundle=bundle.name, dataset=mapping.dataset, captured_at=now,
                      declared_complete=mapping.complete, complete=not incomplete, incomplete_reasons=incomplete,
                      filter=mapping.filter, files=[file_sha])
    metadata = {"capture_id": capture_id, "bundle": bundle.name, "dataset": mapping.dataset,
                "path": str(path.resolve()), "file_sha256": file_sha, "mapping_sha256": sha,
                "accepted": len(rows), "rejected": len({r["row"] for r in rejects}), "filtered": len(filtered),
                "skipped_blank_rows": table.skipped_blank_rows, "licence": mapping.licence,
                "timezone": mapping.timezone, "external_processing_allowed": mapping.external_processing_allowed}
    import os
    import shutil
    import tempfile
    folder.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=folder.parent))
    try:
        write_private(staging / "rows.jsonl", "".join(canonical_json(r.model_dump(mode="json")) + "\n" for r in rows))
        write_private(staging / "rejects.jsonl", "".join(canonical_json(r) + "\n" for r in rejects))
        write_private(staging / "capture.json", capture.model_dump_json(indent=2) + "\n")
        write_private(staging / "metadata.json", canonical_json(metadata) + "\n")
        os.rename(staging, folder)
    except BaseException:
        shutil.rmtree(staging)
        raise
    events = [("ingested", {"capture_id": capture_id, "mapping_sha256": sha,
                           "accepted": len(rows), "rejected": metadata["rejected"], "filtered": len(filtered)})]
    for row in rows:
        events.append(("gate_accepted", {"capture_id": capture_id, "record_id": row.source.record_id,
                                        "content_sha256": row.source.content_sha256,
                                        "unresolved_fields": list(row.unresolved)}))
    for item in rejects:
        events.append(("gate_rejected", {"capture_id": capture_id, "record_id": item["source"]["record_id"],
                                        "field": item["field"], "gate": item["gate"], "reason": item["reason"]}))
    for item in filtered:
        events.append(("row_filtered", {"capture_id": capture_id, "record_id": item["source"]["record_id"], "reason": item["reason"]}))
    for number in table.skipped_blank_rows:
        events.append(("row_skipped", {"capture_id": capture_id, "row": number, "reason": "blank_row"}))
    append_events(bundle, events)
    return metadata | {"reused": False}


def load_capture(folder: Path, bundle: Bundle) -> dict:
    folder = bundle.resolve(folder)
    def read(name):
        return bundle.resolve(folder / name).read_text("utf-8")
    metadata = json.loads(read("metadata.json"))
    capture = Capture.model_validate_json(read("capture.json"))
    rows = [GenericRow.model_validate_json(line) for line in read("rows.jsonl").splitlines()]
    rejects = [json.loads(line) for line in read("rejects.jsonl").splitlines()]
    refs = [r.source for r in rows] + [SourceRef.model_validate(r["source"]) for r in rejects]
    if metadata["bundle"] != bundle.name or capture.bundle != bundle.name or any(r.bundle != bundle.name for r in refs):
        raise MappingError("capture belongs to another bundle")
    if metadata["capture_id"] != folder.name or capture.capture_id != folder.name:
        raise MappingError("capture id does not match its folder")
    if (metadata["dataset"] != capture.dataset or metadata["file_sha256"] not in capture.files
            or metadata["accepted"] != len(rows) or metadata["rejected"] != len({r["row"] for r in rejects})
            or any(r.capture_id != capture.capture_id or r.dataset != capture.dataset
                   or r.url_or_path != metadata["path"] for r in refs)):
        raise MappingError("capture metadata and row references disagree")
    return {"metadata": metadata, "capture": capture, "rows": rows, "rejects": rejects}


def captures(bundle: Bundle) -> list[dict]:
    folder = bundle.resolve(bundle.root / "captures")
    if not folder.exists():
        return []
    return [load_capture(p, bundle) for p in sorted(folder.iterdir()) if p.is_dir() and not p.name.startswith(".pending-")]
