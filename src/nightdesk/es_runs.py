"""Report explicitly reviewed joins between a dated ES schedule and Belgian observations."""

from datetime import date, datetime
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from nightdesk.adapters.gtfs import RULE_VERSION as GTFS_RULE_V1, ENCODED_POINT_RULE_VERSION
from nightdesk.config import ES_ROUTE, INFRABEL_MAPPING_HASHES, PUBLIC_DEMO_BUNDLE
from nightdesk.desk import run_evidence, snapshot
from nightdesk.model import Namespaced, Sha256
from nightdesk.store import ReadSession

RULE_VERSION = "es-run-comparison-v2"


class _ReviewedInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunSelection(_ReviewedInput):
    capture: Sha256
    selection: Sha256


class StationPair(_ReviewedInput):
    scheduled_point: Namespaced
    observed_point: Namespaced


class ReviewedRunJoin(_ReviewedInput):
    reviewed_by: str = Field(min_length=1, max_length=120, pattern=r"\S")
    scheduled: RunSelection
    observed: RunSelection
    stations: list[StationPair] = Field(min_length=1, max_length=100)


def _unique_point(points, identifier):
    matching = [(index, point) for index, point in enumerate(points) if point["point_id"] == identifier]
    if len(matching) != 1:
        raise ValueError("es_comparison_point_missing_or_ambiguous")
    return matching[0]


def _schedule_receipt(reader, capture, run):
    source_hashes = {
        event.payload.get("source_sha256")
        for event in reader.events
        if event.kind == "gtfs_schedule_imported"
        and event.payload.get("capture_id") == capture
        and isinstance(event.payload.get("source_sha256"), str)
        and event.payload.get("rule_version") in (GTFS_RULE_V1, ENCODED_POINT_RULE_VERSION)
    }
    if len(source_hashes) != 1:
        return False
    source_hash, = source_hashes
    evidence = [point["extra"].get("gtfs_evidence") for point in run["points"]]
    return all(isinstance(item, dict)
               and item.get("rule_version") in (GTFS_RULE_V1, ENCODED_POINT_RULE_VERSION)
               and item.get("source_sha256") == source_hash
               for item in evidence)


def _read_join(bundle, path):
    source = bundle.resolve(Path(path))
    with source.open("rb") as stream:
        raw = stream.read(32769)
    if len(raw) > 32768:
        raise ValueError("es_comparison_review_too_large")
    # Refuse duplicate JSON keys instead of silently replacing a reviewed choice.
    def unique_object(items):
        result = dict(items)
        if len(result) != len(items):
            raise ValueError("es_comparison_review_duplicate_key")
        return result

    try:
        return ReviewedRunJoin.model_validate(json.loads(raw, object_pairs_hook=unique_object))
    except (ValueError, RecursionError):
        raise ValueError("es_comparison_review_invalid") from None


def compare_runs(bundle, path, *, reader=None):
    if bundle.nda or bundle.name == PUBLIC_DEMO_BUNDLE:
        raise ValueError("es_comparison_requires_practice_bundle")
    join = _read_join(bundle, path)
    reader = reader or ReadSession(bundle)
    scheduled = run_evidence(bundle, join.scheduled.capture, join.scheduled.selection, reader=reader)
    observed = run_evidence(bundle, join.observed.capture, join.observed.selection, reader=reader)
    schedule_run, observed_run = scheduled["run"], observed["run"]
    train = ES_ROUTE.fullmatch(schedule_run["train_no"].partition(":")[2])
    if (train is None or schedule_run["kind"] != "scheduled"
            or not scheduled["capture"]["dataset"].endswith("_gtfs")
            or observed_run["kind"] != "observed"
            or observed["capture"]["dataset"] not in INFRABEL_MAPPING_HASHES
            or observed_run["train_no"] != f"be:{train[1]}"):
        raise ValueError("es_comparison_train_or_source_mismatch")
    if not _schedule_receipt(reader, join.scheduled.capture, schedule_run):
        raise ValueError("es_comparison_gtfs_import_receipt_required")
    observation = snapshot(bundle, join.observed.capture, reader=reader)
    if observation["metadata"]["mapping_sha256"] != INFRABEL_MAPPING_HASHES[observed["capture"]["dataset"]]:
        raise ValueError("es_comparison_infrabel_mapping_unverified")
    schedule_day = date.fromisoformat(schedule_run["service_date"])
    observed_day = date.fromisoformat(observed_run["service_date"])
    if (observed_day - schedule_day).days not in (0, 1):
        raise ValueError("es_comparison_service_dates_do_not_overlap")

    matched = []
    for pair in join.stations:
        schedule_index, plan = _unique_point(schedule_run["points"], pair.scheduled_point)
        observed_index, actual = _unique_point(observed_run["points"], pair.observed_point)
        events = {}
        for side, sign in (("arrival", "arr"), ("departure", "dep")):
            planned = plan[f"planned_{sign}"]
            source_plan = actual[f"planned_{sign}"]
            actual_time = actual[f"real_{sign}"]
            agrees = (bool(planned and source_plan)
                      and datetime.fromisoformat(planned) == datetime.fromisoformat(source_plan))
            events[side] = {
                "scheduled": planned,
                "infrabel_planned": source_plan,
                "observed": actual_time,
                "schedule_agrees": agrees,
            }
        if not any(event["schedule_agrees"] for event in events.values()):
            raise ValueError("es_comparison_no_matching_planned_instant")
        matched.append((schedule_index, observed_index, {
            "scheduled_point": plan["point_id"],
            "scheduled_native_stop_id": plan["extra"]["gtfs_evidence"].get("stop", {}).get("stop_id"),
            "scheduled_name": plan["name"],
            "scheduled_source": plan["source"],
            "observed_point": actual["point_id"],
            "observed_name": actual["name"],
            "observed_source": actual["source"],
            **events,
        }))

    matched.sort(key=lambda item: item[0])
    for side in (0, 1):
        sequence = [item[side] for item in matched]
        if sequence != sorted(set(sequence)):
            raise ValueError("es_comparison_station_order_or_identity_conflict")
    return {
        "kind": "es_run_comparison",
        "rule_version": RULE_VERSION,
        "bundle": bundle.name,
        "train": train[1],
        "review": join.model_dump(mode="json"),
        "scheduled": scheduled,
        "observed": observed,
        "stations": [item[2] for item in matched],
        "provenance": [*scheduled["provenance"], *observed["provenance"]],
        "unreviewed_points": {"scheduled": len(schedule_run["points"]) - len(matched),
                              "observed": len(observed_run["points"]) - len(matched)},
        "limits": [
            "This review matches the listed stations only.",
            "A human selected the two runs and station identities. Each pair shares a planned instant.",
            "Missing stations and missing observations remain unknown.",
            *[f"Partial {side} capture: " + ", ".join(report["capture"]["incomplete_reasons"])
              for side, report in (("schedule", scheduled), ("Infrabel", observed))
              if not report["capture"]["complete"]],
        ],
    }
