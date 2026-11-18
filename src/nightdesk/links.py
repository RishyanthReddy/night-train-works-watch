"""Explicit journey crosswalks from a source or a named person's confirmation."""

from collections import defaultdict
from datetime import date

from nightdesk.audit import append_event
from nightdesk.config import Bundle
from nightdesk.model import JourneyLink, JourneyLinkMember, PathLeg
from nightdesk.store import hash_value, load_revision, ReadSession


def link_id(link: JourneyLink) -> str:
    return hash_value({"journey_id": link.journey_id, "basis": link.basis, "actor": link.confirmed_by,
                       "members": sorted((m.network, m.train_no, m.service_date_rule) for m in link.members),
                       "dataset": link.source.dataset if link.source else None})


def save_link(bundle: Bundle, link: JourneyLink) -> str:
    from nightdesk.intake.mapping import write_private
    if any(m.source.bundle != bundle.name for m in link.members) or link.source and link.source.bundle != bundle.name:
        raise ValueError("cross_bundle_link")
    identifier = link_id(link)
    path = bundle.resolve(bundle.root / "links" / (identifier + ".json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        write_private(path, link.model_dump_json(indent=2) + "\n")
    except FileExistsError:
        load_link(bundle, identifier)
    else:
        append_event(bundle, "journey_link_recorded", {"link_id": identifier, "basis": link.basis,
                                                       "confirmed_by": link.confirmed_by,
                                                       "input_refs": [m.source.model_dump(mode="json", exclude={"field_evidence"}) for m in link.members]})
    return identifier


def load_link(bundle: Bundle, identifier: str) -> JourneyLink:
    import re
    if not re.fullmatch(r"[a-f0-9]{64}", identifier):
        raise ValueError("invalid_link_id")
    path = bundle.resolve(bundle.root / "links" / (identifier + ".json"))
    link = JourneyLink.model_validate_json(path.read_text("utf-8"))
    if link_id(link) != identifier or any(m.source.bundle != bundle.name for m in link.members):
        raise ValueError("link_reference_mismatch")
    return link


def links(bundle: Bundle) -> list[JourneyLink]:
    path = bundle.resolve(bundle.root / "links")
    return [load_link(bundle, p.stem) for p in sorted(path.glob("*.json"))] if path.exists() else []


def import_links(bundle: Bundle, capture_id: str) -> list[str]:
    from nightdesk.intake.mapping import captures
    capture = next((c for c in captures(bundle) if c["capture"].capture_id == capture_id), None)
    if capture is None or capture["metadata"]["record_type"] != "JourneyLinkMember":
        raise ValueError("select_a_journey_crosswalk_capture")
    grouped = defaultdict(list)
    for member in capture["typed_rows"]:
        grouped[member.journey_id].append(member)
    return [save_link(bundle, JourneyLink(journey_id=journey, members=members, basis="source", source=members[0].source))
            for journey, members in sorted(grouped.items())]


def confirm_link(bundle: Bundle, journey_id: str, revision_ids: list[str], actor: str,
                 service_date_rule: str) -> str:
    if not revision_ids or len(set(revision_ids)) != len(revision_ids):
        raise ValueError("select_distinct_path_leg_revisions")
    members = []
    reader = ReadSession(bundle)
    for identifier in revision_ids:
        revision = load_revision(bundle, identifier, reader=reader)
        if not isinstance(revision.payload, PathLeg):
            raise ValueError("link_member_must_be_path_leg")
        leg = revision.payload
        members.append(JourneyLinkMember(source=revision.source, journey_id=journey_id,
                                          network=leg.network, train_no=leg.train_no,
                                          service_date_rule=service_date_rule))
    return save_link(bundle, JourneyLink(journey_id=journey_id, members=members, basis="human", confirmed_by=actor))


def coverage_by_train(link: JourneyLink, service_date: date) -> dict:
    """Compile the explicit crosswalk once for a selected service date."""
    coverage = {}
    for member in link.members:
        key = (member.network, member.train_no)
        if coverage.get(key, (False, None))[0]:
            continue
        if member.service_date_rule == "*":
            coverage[key] = (True, None)
            continue
        try:
            day = date.fromisoformat(member.service_date_rule)
        except ValueError:
            coverage[key] = (False, "unsupported_service_date_rule")
        else:
            if day == service_date:
                coverage[key] = (True, None)
            else:
                coverage.setdefault(key, (False, "unlinked"))
    return coverage


def covers(link: JourneyLink, leg: PathLeg, service_date: date) -> tuple[bool, str | None]:
    return coverage_by_train(link, service_date).get((leg.network, leg.train_no), (False, "unlinked"))


def find_link(leg: PathLeg, service_date: date, candidates: list[JourneyLink]):
    matched = [link for link in candidates if covers(link, leg, service_date)[0]]
    if len(matched) == 1:
        return matched[0], None
    if len(matched) > 1:
        return None, "ambiguous_journey_link"
    reason = "unsupported_service_date_rule" if any(covers(link, leg, service_date)[1] == "unsupported_service_date_rule" for link in candidates) else "unlinked"
    return None, reason
