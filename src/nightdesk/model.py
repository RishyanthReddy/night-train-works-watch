"""Canonical records (KICKOFF "Canonical records").

All datetimes are timezone-aware. Floats must be finite. Every model is frozen and
refuses unknown fields. `bundle` must name a known bundle (see config.get_bundle).
"""

from __future__ import annotations

from typing import Annotated, Any, Union, Literal
from datetime import date, time
import re

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
    field_validator,
)
from typing_extensions import TypeAliasType

from nightdesk.config import get_bundle, WORK_EFFECTS
from nightdesk.timeutil import utc

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
    """One log line. Hash fields may be None only in a preserved Phase 0 legacy log."""

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


def _namespace(value: str) -> str:
    if not re.fullmatch(r"[^\s:]+:[^\s:]+", value):
        raise ValueError("id_not_namespaced")
    return value


Namespaced = Annotated[NonEmpty, AfterValidator(_namespace)]


class _Payload(_Record):
    extra: dict[str, JSONValue] = Field(default_factory=dict)
    unresolved: dict[str, JSONValue] = Field(default_factory=dict)


class WorkNotice(_Payload):
    work_id: str | None = None
    country: NonEmpty
    line: Namespaced | None = None
    from_place: str = ""
    to_place: str = ""
    from_point_id: Namespaced | None = None
    to_point_id: Namespaced | None = None
    date_start: date
    date_end: date
    clock_from: time | None = None
    clock_to: time | None = None
    weekdays: list[int] | None = None
    recurrence: Literal["periodical", "continuous", "unknown"] = "unknown"
    effect: str = "unknown"
    description: str = ""
    published_at: AwareDatetime | None = None
    proposed_by: Literal["adapter", "llm", "manual"] = "adapter"
    timezone: str | None = None

    @field_validator("effect")
    @classmethod
    def allowed_effect(cls, value):
        if value not in WORK_EFFECTS:
            raise ValueError("effect_not_in_canonical_vocabulary")
        return value


class BoundaryEvent(_Payload):
    point_id: Namespaced | None = None
    place_name: str = ""
    kind: Literal["arrival", "departure", "pass", "handover", "unknown"] = "unknown"
    at: AwareDatetime | None = None
    raw_time: str = ""
    timezone: str | None = None
    unresolved_reason: str | None = None

    @model_validator(mode="before")
    @classmethod
    def unresolved_time(cls, values):
        if not isinstance(values, dict):
            return values
        values = dict(values)
        if values.get("at") is None and values.get("unresolved_reason") is None:
            values["unresolved_reason"] = "missing_time"
        if values.get("at") is not None and values.get("unresolved_reason") is not None:
            raise ValueError("resolved_time_cannot_have_unresolved_reason")
        return values


class PathLeg(_Payload):
    journey_ref: str | None = None
    request_id: str | None = None
    network: NonEmpty
    train_no: Namespaced
    sequence: int | None = None
    operating_dates: list[date]
    entry: BoundaryEvent | None = None
    exit: BoundaryEvent | None = None
    source_status: str | None = None


class JourneyLinkMember(_Payload):
    source: SourceRef
    journey_id: NonEmpty
    network: NonEmpty
    train_no: Namespaced
    # v1 source dates are ISO dates or '*': same-service-date across networks.
    # Other rules remain unsupported/unknown until a sourced adapter exists.
    service_date_rule: NonEmpty


class JourneyLink(_Payload):
    journey_id: NonEmpty
    members: list[JourneyLinkMember]
    basis: Literal["source", "human"]
    source: SourceRef | None = None
    confirmed_by: str | None = None

    @model_validator(mode="after")
    def basis_has_evidence(self):
        if self.basis == "source" and self.source is None:
            raise ValueError("source_link_needs_source")
        if self.basis == "human" and not (self.confirmed_by or "").strip():
            raise ValueError("human_link_needs_actor")
        if not self.members:
            raise ValueError("journey_link_has_no_members")
        bundles = {m.source.bundle for m in self.members}
        if self.source is not None:
            bundles.add(self.source.bundle)
        if len(bundles) != 1:
            raise ValueError("journey_link_crosses_bundles")
        return self


class RunPoint(_Payload):
    point_id: Namespaced
    name: str = ""
    line_dep: Namespaced | None = None
    line_arr: Namespaced | None = None
    planned_arr: AwareDatetime | None = None
    planned_dep: AwareDatetime | None = None
    real_arr: AwareDatetime | None = None
    real_dep: AwareDatetime | None = None
    delay_arr_s: int | None = None
    delay_dep_s: int | None = None
    source: SourceRef | None = None


class RunRow(RunPoint):
    source: SourceRef
    service_date: date
    train_no: Namespaced
    kind: Literal["observed", "scheduled"] = "observed"
    trip_id: str | None = None


class TrainRun(_Payload):
    service_date: date
    train_no: Namespaced
    kind: Literal["observed", "scheduled"]
    trip_id: str | None = None
    points: list[RunPoint]
    input_refs: list[SourceRef] = Field(default_factory=list)
    rule_version: str = "runs-v1"
    path_unresolved: bool = False


class Segment(_Record):
    a: RunPoint
    b: RunPoint
    line: Namespaced | None = None
    planned_s: int | None = None
    input_refs: list[SourceRef] = Field(default_factory=list)
    rule_version: str = "runs-v1"


class Revision(_Record):
    revision_id: Sha256
    subject_type: Literal["work", "path_leg"]
    subject_key: NonEmpty
    payload: WorkNotice | PathLeg
    source: SourceRef
    source_status: str | None = None
    predecessor: Sha256 | None = None
    predecessor_basis: Literal["source_field", "human"] | None = None
    identity: Literal["certain", "uncertain"]
    import_status: Literal["accepted", "unresolved"] = "accepted"

    @model_validator(mode="after")
    def payload_matches_type(self):
        if (self.subject_type == "work") != isinstance(self.payload, WorkNotice):
            raise ValueError("subject_payload_mismatch")
        if (self.predecessor is None) != (self.predecessor_basis is None):
            raise ValueError("predecessor_basis_required_with_predecessor")
        if self.predecessor == self.revision_id:
            raise ValueError("self_predecessor")
        return self


class FieldDiff(_Record):
    field: NonEmpty
    old: JSONValue
    new: JSONValue
    old_present: bool = True
    new_present: bool = True


class ChangeSet(_Record):
    old_revision: str | None = None
    new_revision: str | None = None
    old_capture: str | None = None
    new_capture: str | None = None
    basis: NonEmpty
    field_diffs: list[FieldDiff] = Field(default_factory=list)
    affected_dates: list[date] = Field(default_factory=list)
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)
    # Descriptive window membership, also available when R2 blocks conclusions.
    # Every item retains the revision/source and the reason for exclusion.
    membership_changes: list[dict[str, JSONValue]] = Field(default_factory=list)
    status: Literal["compared", "identity_uncertain", "comparison_unavailable"]
    reason: str | None = None
    input_refs: list[SourceRef] = Field(default_factory=list)
    rule_version: str = "changes-v2"


class Exposure(_Record):
    service_date: date
    train_no: Namespaced
    work_revision: Sha256
    outcome: Literal["A", "B", "unlocated", "time_unknown"]
    reasons: list[str] = Field(default_factory=list)
    overlap_window: list[AwareDatetime] | None = None
    gate_results: list[GateResult] = Field(default_factory=list)
    input_refs: list[SourceRef] = Field(default_factory=list)
    place_resolution: dict[str, JSONValue] = Field(default_factory=dict)
    rule_version: str = "match-v1"


class ConsistencyFinding(_Record):
    rule: NonEmpty
    rule_version: NonEmpty
    input_refs: list[SourceRef]
    result: Literal["mismatch", "agrees_on_checked_fields", "unknown"]
    reason: str | None = None
    detail: dict[str, JSONValue] = Field(default_factory=dict)


class ReviewDecision(_Record):
    revision_id: Sha256
    actor: NonEmpty
    disposition: Literal["accepted_locally", "needs_clarification", "rejected_locally"]
    reason: NonEmpty
    evidence: list[SourceRef] = Field(default_factory=list)
    at: AwareDatetime
    stale: bool = False


class FollowUp(_Record):
    follow_up_id: NonEmpty
    revision_id: Sha256
    owner: NonEmpty
    question: NonEmpty
    depends_on: str | None = None
    deadline: AwareDatetime | None = None
    deadline_source: SourceRef | None = None
    status: Literal["open", "answered", "reopened"] = "open"

    @model_validator(mode="after")
    def no_deadline_without_source(self):
        if self.deadline is not None and self.deadline_source is None:
            raise ValueError("deadline_requires_source")
        return self


class Refusal(_Record):
    reason_code: str
    detail: str
    what_would_fix_it: str
