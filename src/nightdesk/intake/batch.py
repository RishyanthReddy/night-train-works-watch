"""A declared multi-file capture: all constituent inputs and mappings are explicit.

Individual source captures remain immutable. A batch lists those input captures
and revision ids; missing or rejected inputs make its effective completeness false.
"""

from datetime import datetime, timezone
from pathlib import Path
import re

from pydantic import Field, model_validator

from nightdesk.audit import append_event, canonical_json
from nightdesk.model import Capture
from nightdesk.store import hash_value, ReadSession, subject_key
from nightdesk.intake.mapping import (_Config, check_input, confirm_mapping, digest, ingest, load_capture,
                                      load_mapping, safe_yaml, write_private, _confirmed, MappingError)


class BatchFile(_Config):
    role: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    path: str = Field(min_length=1)
    mapping: str = Field(min_length=1)


class BatchManifest(_Config):
    version: int
    dataset: str = Field(min_length=1)
    label: str = Field(min_length=1)
    complete: bool = False
    files: list[BatchFile] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_contract(self):
        if self.version != 1 or len({f.role for f in self.files}) != len(self.files):
            raise ValueError("batch version must be 1 and roles must be unique")
        return self


def load_manifest(path, bundle):
    from nightdesk.demo import demo_input

    path = Path(path)
    check_input(path, bundle)
    approved = demo_input(bundle, path, kind={"capture_manifest"})
    raw = path.read_bytes()
    if approved and digest(raw) != approved.sha256:
        raise MappingError("demo_asset_hash_mismatch")
    manifest = BatchManifest.model_validate(safe_yaml(raw.decode("utf-8")))
    files = []
    for item in manifest.files:
        source, mapping = (path.parent / item.path).resolve(), (path.parent / item.mapping).resolve()
        check_input(source, bundle);check_input(mapping, bundle)
        spec, sha = load_mapping(mapping)
        if spec.dataset != manifest.dataset:
            raise MappingError("all batch file mappings must declare the batch dataset")
        files.append((item, source, mapping, spec, sha))
    return manifest, digest(raw), files


def confirm_batch(path, bundle, actor):
    _, _, files = load_manifest(path, bundle)
    return [confirm_mapping(mapping, bundle, actor) for _, _, mapping, _, _ in files]


def ingest_batch(path, bundle):
    manifest, manifest_sha, files = load_manifest(path, bundle)
    if any(not _confirmed(bundle, sha) for _, _, _, _, sha in files):
        append_event(bundle, "batch_refused", {"reason": "mapping_not_confirmed", "manifest_sha256": manifest_sha})
        raise MappingError("mapping_not_confirmed: confirm the current batch mappings in this bundle first")
    children, failures, filters = {}, [], {}
    for item, source, mapping, spec, _ in files:
        filters[item.role] = spec.filter
        try:
            result = ingest(source, mapping, bundle)
        except (ValueError, OSError):
            failures.append({"role": item.role, "reason": "input_missing_or_parse_failed"})
        else:
            children[item.role] = result["capture_id"]
    identifier = hash_value([bundle.name, manifest.dataset, manifest_sha, manifest.complete, children, failures])
    folder = bundle.resolve(bundle.root / "batches" / identifier)
    if folder.exists():
        return load_batch(bundle, identifier)
    reader = ReadSession(bundle)
    constituent = [load_capture(bundle.root / "captures" / cid, bundle, reader=reader) for cid in children.values()]
    reasons = [] if manifest.complete else ["not_declared_complete"]
    if failures:
        reasons.append("missing_or_unparsed_files")
    if any(not c["capture"].complete for c in constituent):
        reasons.append("incomplete_constituent_capture")
    revision_ids = list(dict.fromkeys(i for c in constituent for i in c["capture"].revision_ids))
    from nightdesk.model import WorkNotice, PathLeg
    subjects = [(type(p).__name__, subject_key(p)[0]) for c in constituent for p in c.get("typed_rows", [])
                if isinstance(p, (WorkNotice, PathLeg))]
    if len(set(subjects)) != len(subjects):
        reasons.append("duplicate_subject")
    capture = Capture(capture_id=identifier, bundle=bundle.name, dataset=manifest.dataset,
                      captured_at=datetime.now(timezone.utc), declared_complete=manifest.complete,
                      complete=not reasons, incomplete_reasons=reasons, filter={"roles": filters},
                      files=[manifest_sha] + [sha for c in constituent for sha in c["capture"].files], revision_ids=revision_ids)
    document = {"capture": capture.model_dump(mode="json"), "children": children, "failures": failures,
                "metadata": {"format_version": 2, "path": str(Path(path).resolve()), "label": manifest.label, "record_type": "Batch",
                             "record_types": sorted({c["metadata"]["record_type"] for c in constituent}),
                             "dataset": manifest.dataset, "bundle": bundle.name}}
    import os
    import tempfile
    import shutil
    folder.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=folder.parent))
    try:
        manifest_raw = Path(path).read_bytes()
        if digest(manifest_raw) != manifest_sha:
            raise MappingError("manifest changed while reading; retry")
        write_private(staging / "manifest.yaml", manifest_raw.decode("utf-8"))
        write_private(staging / "batch.json", canonical_json(document) + "\n")
        os.rename(staging, folder)
    except BaseException:
        shutil.rmtree(staging)
        raise
    append_event(bundle, "batch_imported", {"capture_id": identifier, "manifest_sha256": manifest_sha,
                                           "children": children, "complete": capture.complete, "failures": failures,
                                           "revision_ids": revision_ids, "declared_complete": manifest.complete,
                                           "batch_sha256": digest((folder / "batch.json").read_bytes())})
    return load_batch(bundle, identifier)


def load_batch(bundle, identifier, *, reader=None):
    import json
    from nightdesk.model import WorkNotice, PathLeg
    reader = reader or ReadSession(bundle)
    reader.check_bundle(bundle)
    if identifier in reader.batch_cache:
        return reader.batch_cache[identifier]
    if not re.fullmatch(r"[a-f0-9]{64}", identifier):
        raise ValueError("invalid_batch_id")
    path = bundle.resolve(bundle.root / "batches" / identifier / "batch.json")
    raw = path.read_bytes()
    record = json.loads(raw)
    capture = Capture.model_validate(record["capture"])
    if capture.capture_id != identifier or capture.bundle != bundle.name or record["metadata"]["bundle"] != bundle.name:
        raise ValueError("batch_reference_mismatch")
    reader.events
    imported = reader.batch_imports.get(identifier, {})
    if imported.get("batch_sha256") and imported["batch_sha256"] != digest(raw):
        raise ValueError("batch_artifact_hash_mismatch")
    if "complete" in imported and imported["complete"] != capture.complete:
        raise ValueError("batch_audit_completeness_mismatch")
    version = record["metadata"].get("format_version", 1)
    manifest_path = path.parent / "manifest.yaml" if version == 2 else Path(record["metadata"]["path"])
    check_input(manifest_path, bundle)
    manifest = None
    if capture.files and manifest_path.exists():
        manifest_raw = manifest_path.read_bytes()
        if digest(manifest_raw) == capture.files[0]:
            manifest = BatchManifest.model_validate(safe_yaml(manifest_raw.decode("utf-8")))
    if version == 2 and (manifest is None or not imported.get("batch_sha256")):
        raise ValueError("batch_declaration_evidence_missing")
    identity = [bundle.name, capture.dataset, capture.files[0]] if capture.files else []
    if version == 2:
        identity.append(manifest.complete)
    identity += [record["children"], record["failures"]]
    if hash_value(identity) != identifier:
        raise ValueError("batch_hash_mismatch")
    roles = [item.role for item in manifest.files] if manifest else sorted(record["children"])
    if manifest:
        failed = [f["role"] for f in record["failures"]]
        if (manifest.dataset != capture.dataset or record["metadata"]["label"] != manifest.label
                or len(set(failed)) != len(failed) or set(failed) & record["children"].keys()
                or set(roles) != set(failed) | record["children"].keys()):
            raise ValueError("batch_manifest_reference_mismatch")
    children = [load_capture(bundle.root / "captures" / record["children"][role], bundle, reader=reader)
                for role in roles if role in record["children"]]
    if any(c["capture"].dataset != capture.dataset for c in children):
        raise ValueError("batch_dataset_mismatch")
    ids = list(dict.fromkeys(i for c in children for i in c["capture"].revision_ids))
    if ids != capture.revision_ids:
        raise ValueError("batch_revision_refs_mismatch")
    declared = manifest.complete if manifest else capture.declared_complete
    reasons = [] if declared else ["not_declared_complete"]
    if record["failures"]:
        reasons.append("missing_or_unparsed_files")
    if any(not c["capture"].complete for c in children):
        reasons.append("incomplete_constituent_capture")
    keys = [(type(p).__name__, subject_key(p)[0]) for c in children for p in c.get("typed_rows", [])
            if isinstance(p, (WorkNotice, PathLeg))]
    if len(set(keys)) != len(keys):
        reasons.append("duplicate_subject")
    if manifest is None:
        capture = capture.model_copy(update={"complete": False,
            "incomplete_reasons": list(dict.fromkeys(reasons + ["legacy_declaration_unverified"]))})
    elif (capture.declared_complete != declared or capture.complete != (not reasons)
          or capture.incomplete_reasons != reasons):
        legacy_unverified = version == 1 and any("legacy_declaration_unverified" in c["capture"].incomplete_reasons for c in children)
        if legacy_unverified:
            capture = capture.model_copy(update={"complete": False, "incomplete_reasons": reasons})
        else:
            raise ValueError("batch_completeness_mismatch")
    if manifest and not record["failures"]:
        expected_files = [capture.files[0]] + [sha for c in children for sha in c["capture"].files]
        expected_filter = {"roles": {role: c["capture"].filter for role, c in zip(roles, children)}}
        if capture.files != expected_files or capture.filter != expected_filter:
            raise ValueError("batch_files_or_filter_mismatch")
    result = {**record, "capture": capture, "rows": [r for c in children for r in c["rows"]],
              "typed_rows": [r for c in children for r in c.get("typed_rows", [])],
              "rejects": [r for c in children for r in c["rejects"]]}
    reader.batch_cache[identifier] = result
    return result


def batches(bundle, *, reader=None):
    folder = bundle.resolve(bundle.root / "batches")
    reader = reader or ReadSession(bundle)
    return [load_batch(bundle, p.name, reader=reader) for p in sorted(folder.iterdir()) if not p.name.startswith(".pending-")] if folder.exists() else []
