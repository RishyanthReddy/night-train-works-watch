"""Phase 0 canonical records (KICKOFF "Canonical records").

All datetimes are timezone-aware. Floats must be finite. Every model is frozen and
refuses unknown fields. `bundle` must name a known bundle (see config.get_bundle).
"""

from __future__ import annotations

from typing import Annotated, Any, Union

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)
from typing_extensions import TypeAliasType

from nightdesk.config import get_bundle

JSONValue = TypeAliasType(
    "JSONValue",
    Union[None, bool, int, float, str, list["JSONValue"], dict[str, "JSONValue"]],
)

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
NonEmpty = Annotated[str, StringConstraints(min_length=1)]


def _known_bundle(name: str) -> str:
    get_bundle(name)  # raises BundleError (a ValueError) for unknown/unsafe names
    return name


BundleName = Annotated[str, AfterValidator(_known_bundle)]


class _Record(BaseModel):
    # allow_inf_nan=False rejects NaN/Infinity anywhere a float is validated,
    # including inside nested JSONValue lists and dicts.
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class SourceRef(_Record):
    """One raw input record. References the source; never holds its full text."""

    bundle: BundleName
    dataset: NonEmpty
    record_id: NonEmpty
    capture_id: NonEmpty
    content_sha256: Sha256
    captured_at: AwareDatetime
    url_or_path: NonEmpty
    licence: NonEmpty
    field_evidence: dict[str, str] | None = None


class Capture(_Record):
    """One import of one source. `complete` is the effective value computed at import."""

    capture_id: NonEmpty
    bundle: BundleName
    dataset: NonEmpty
    captured_at: AwareDatetime
    declared_complete: bool = False
    complete: bool = False
    incomplete_reasons: list[str] = Field(default_factory=list)
    filter: dict[str, JSONValue] | None = None
    files: list[Sha256] = Field(default_factory=list)
    revision_ids: list[str] = Field(default_factory=list)


class GenericRow(_Record):
    """A table row that fits no typed record: mapped fields plus unused source fields."""

    source: SourceRef
    fields: dict[str, JSONValue]
    extra: dict[str, JSONValue] = Field(default_factory=dict)
    unresolved: dict[str, JSONValue] = Field(default_factory=dict)


class GateResult(_Record):
    gate: NonEmpty
    passed: bool
    reason_code: str | None = None
    detail: str = ""


class AuditEvent(_Record):
    """One audit log line. Phase 0: append-only, no hash chain (prev_hash/hash stay None)."""

    seq: Annotated[int, Field(ge=0)]
    ts: AwareDatetime
    bundle: BundleName
    kind: NonEmpty
    payload: dict[str, JSONValue] = Field(default_factory=dict)
    prev_hash: Sha256 | None = None
    hash: Sha256 | None = None


def source_ref_payload(ref: SourceRef) -> dict[str, Any]:
    """Audit payload that points at a source record without copying its text.

    Drops `field_evidence` (quoted source spans), keeping only the reference.
    """
    return ref.model_dump(mode="json", exclude={"field_evidence"})
