"""Reviewed, sourced station aliases. No network lookup or fuzzy identity guess."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re

from pydantic import BaseModel, ConfigDict, StrictBool, field_validator
import yaml

from nightdesk.audit import append_event, read_events, canonical_json
from nightdesk.config import Bundle
from nightdesk.intake.mapping import check_input, write_private, safe_yaml
from nightdesk.model import SourceRef


class AliasRow(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    name: str
    point_id: str
    source: str
    licence: str
    reviewed: StrictBool

    @field_validator('name', 'source', 'licence')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('alias_evidence_required')
        return value

    @field_validator('point_id')
    @classmethod
    def namespaced(cls, value):
        if not re.fullmatch(r'[^\s:]+:[^\s:]+', value):
            raise ValueError('alias_point_not_namespaced')
        return value

    @field_validator('reviewed')
    @classmethod
    def must_be_reviewed(cls, value):
        if value is not True:
            raise ValueError('alias_not_reviewed')
        return value


def normal_name(name):
    return ' '.join(name.casefold().split())


@dataclass(frozen=True)
class Resolution:
    point_id: str | None
    candidates: tuple[str, ...]
    reason: str | None
    input_refs: tuple[SourceRef, ...] = ()
    evidence: tuple[dict, ...] = ()

    def as_dict(self):
        return dict(point_id=self.point_id, candidates=list(self.candidates), reason=self.reason,
                    evidence=list(self.evidence))


class StationResolver:
    def __init__(self, bundle, table_id=None, rows=(), refs=()):
        self.bundle = bundle
        self.table_id = table_id
        self.index = {}
        for row, ref in zip(rows, refs):
            self.index.setdefault(normal_name(row.name), []).append((row, ref))

    def resolve(self, name):
        entries = self.index.get(normal_name(name), [])
        ids = tuple(sorted({row.point_id for row, _ in entries}))
        return Resolution(ids[0] if len(ids) == 1 else None, ids,
                          'alias_ambiguous' if len(ids) > 1 else 'alias_not_found' if not ids else None,
                          tuple(ref for _, ref in entries), tuple(row.model_dump() for row, _ in entries))


def import_aliases(path, bundle: Bundle, actor: str):
    from nightdesk.demo import demo_input

    if not actor.strip():
        raise ValueError('alias_reviewer_required')
    check_input(path, bundle)
    from pathlib import Path
    path = Path(path)
    approved = demo_input(bundle, path, kind={"aliases"})
    raw = path.read_bytes()
    body = safe_yaml(raw.decode("utf-8"))
    if not isinstance(body, dict) or set(body) != {'version', 'aliases'} or type(body['version']) is not int or body['version'] != 1:
        raise ValueError('alias_table_version_or_shape')
    if not isinstance(body['aliases'], list) or not body['aliases']:
        raise ValueError('alias_rows_required')
    rows = [AliasRow.model_validate(row) for row in body['aliases']]
    identifier = hashlib.sha256(raw).hexdigest()
    if approved and identifier != approved.sha256:
        raise ValueError("demo_asset_hash_mismatch")
    target = bundle.resolve(bundle.root / 'aliases' / (identifier + '.json'))
    if target.exists():
        load_aliases(bundle, identifier)
        return identifier
    captured = datetime.now(timezone.utc)
    payload = dict(bundle=bundle.name, file_sha256=identifier, actor=actor,
                   captured_at=captured.isoformat(), rows=[row.model_dump() for row in rows])
    text = canonical_json(payload) + '\n'
    target.parent.mkdir(parents=True, exist_ok=True)
    write_private(target, text)
    append_event(bundle, 'aliases_confirmed', dict(table_id=identifier, actor=actor,
                 table_sha256=hashlib.sha256(text.encode()).hexdigest()))
    return identifier


def load_aliases(bundle: Bundle, table_id=None, *, reader=None):
    if reader:
        reader.check_bundle(bundle)
    events = reader.events if reader else read_events(bundle)
    confirmed = {e.payload['table_id']: e.payload for e in events if e.kind == 'aliases_confirmed'}
    if table_id is None:
        if not confirmed:
            return StationResolver(bundle.name)
        if len(confirmed) != 1:
            raise ValueError('select_one_alias_table')
        table_id = next(iter(confirmed))
    if not isinstance(table_id, str) or not re.fullmatch(r'[a-f0-9]{64}', table_id) or table_id not in confirmed:
        raise ValueError('alias_table_not_confirmed_in_bundle')
    path = bundle.resolve(bundle.root / 'aliases' / (table_id + '.json'))
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != confirmed[table_id]['table_sha256']:
        raise ValueError('alias_table_hash_mismatch')
    payload = json.loads(raw)
    if payload['bundle'] != bundle.name or payload['file_sha256'] != table_id:
        raise ValueError('alias_bundle_or_table_mismatch')
    rows = [AliasRow.model_validate(row) for row in payload['rows']]
    refs = [SourceRef(bundle=bundle.name, dataset='station_aliases', record_id=f'row:{i+1}', capture_id=table_id,
                     content_sha256=hashlib.sha256(canonical_json(row.model_dump()).encode()).hexdigest(),
                     captured_at=payload['captured_at'], url_or_path=row.source, licence=row.licence) for i, row in enumerate(rows)]
    return StationResolver(bundle.name, table_id, rows, refs)
