"""Private bundle-local replay, committed public fixtures require a licence label."""
import hashlib
import json
from pathlib import Path
from nightdesk.audit import append_event, canonical_json, read_events
from nightdesk.intake.mapping import check_input, write_private
from nightdesk.config import MAX_MODEL_RESPONSE_BYTES


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def save(bundle, text, proposal, *, dataset, licence):
    body = dict(version=1, bundle=bundle.name, dataset=dataset, licence=licence,
                source_text=text, proposal=proposal)
    identifier = digest(body)
    path = bundle.resolve(bundle.root / 'llm' / 'cache' / (identifier + '.json'))
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = canonical_json(body) + '\n'
    if path.exists():
        if path.read_text() != rendered: raise ValueError('cache_content_mismatch')
    else:
        write_private(path, rendered)
        append_event(bundle, 'text_cached', {'cache_id': identifier, 'dataset': dataset})
    return path


def replay(bundle, path, text, dataset, licence):
    check_input(path, bundle)
    path = Path(path)
    local = False
    try:
        bundle.resolve(path); local = True
    except ValueError:
        pass
    if bundle.nda and not local:
        raise ValueError('nda_replay_requires_own_bundle_cache')
    if path.stat().st_size>MAX_MODEL_RESPONSE_BYTES: raise ValueError('replay_input_mismatch')
    try:
        body = json.loads(path.read_text())
    except (ValueError, RecursionError):
        raise ValueError('replay_input_mismatch') from None
    if (not isinstance(body, dict) or type(body.get('version')) is not int or body['version'] != 1
            or any(not isinstance(body.get(k), str) for k in ('source_text','dataset','licence'))
            or ('bundle' in body and not isinstance(body['bundle'],str))
            or body['source_text'] != text):
        raise ValueError('replay_input_mismatch')
    if local:
        identifier = digest(body)
        if body.get('bundle') != bundle.name or path.stem != identifier:
            raise ValueError('cache_bundle_or_hash_mismatch')
        if not any(e.kind == 'text_cached' and e.payload.get('cache_id') == identifier for e in read_events(bundle)):
            raise ValueError('cache_audit_evidence_missing')
    elif body.get('licence') not in {'synthetic', 'CC0'} or licence not in {'synthetic', 'CC0'}:
        raise ValueError('replay_requires_public_or_synthetic_inputs')
    if body.get('dataset') != dataset or body.get('licence') != licence:
        raise ValueError('replay_dataset_mismatch')
    from nightdesk.intake.text import Proposal
    try:
        return Proposal.model_validate(body.get('proposal')).model_dump()
    except ValueError:
        raise ValueError('replay_proposal_invalid') from None
