"""Mistral-only HTTPS proposals, explicit consent, or offline replay/off."""
import hashlib
import http.client
import json
import os
import re
from pathlib import Path
from nightdesk.audit import append_event, read_events, canonical_json
from nightdesk.config import (PUBLIC_DEMO_BUNDLE, MISTRAL_HOST, MISTRAL_MODEL, MISTRAL_TIMEOUT_SECONDS,
                              MISTRAL_MAX_TOKENS, MAX_MODEL_RESPONSE_BYTES)
from nightdesk.intake.mapping import load_mapping, check_input
from nightdesk.intake.text import text_guard, validate_proposal, Proposal
from nightdesk.llm import cache

PROMPT_VERSION = 'quoted-work-v2'


def consent(bundle, actor, *, allow):
    if bundle.name == PUBLIC_DEMO_BUNDLE and allow:
        raise ValueError('demo_live_model_disabled')
    if not actor.strip(): raise ValueError('consent_actor_required')
    append_event(bundle,'model_consent',{'actor':actor,'provider':'mistral','allowed':bool(allow)})


def allowed(bundle):
    events=[e for e in read_events(bundle) if e.kind=='model_consent' and e.payload.get('provider')=='mistral']
    return bool(events and events[-1].payload.get('allowed') is True)


def _send(text):
    key=os.environ.get('MISTRAL_API_KEY')
    if not key: raise ValueError('mistral_key_unavailable')
    if not re.fullmatch(r'[\x21-\x7e]+',key): raise ValueError('mistral_key_invalid_format')
    from nightdesk.model import WorkNotice
    instruction=('Return JSON only: {"fields": {...}, "quotes": {"field": "exact source quote"}}. '
        'Propose only WorkNotice fields supported by the source. Every nonempty field needs a quote '
        'containing its literal value. Every value in "quotes" must be a JSON string, including quotes '
        'for arrays or numbers. For example, {"fields":{"weekdays":[1,2]},"quotes":{"weekdays":"[1,2]"}} '
        'uses the string "[1,2]" only if those exact characters appear in the notice. ISO dates may '
        'quote DD.MM.YYYY. Omit quotes for unknown (null) or empty field values. '
        'No extra/unresolved/proposed_by fields, actions, commands or decisions. Use ISO dates and HH:MM clocks. '
        'Allowed schema: '+canonical_json(WorkNotice.model_json_schema()))
    payload=dict(model=MISTRAL_MODEL,temperature=0,response_format={'type':'json_object'},max_tokens=MISTRAL_MAX_TOKENS,
        messages=[{'role':'system','content':instruction},{'role':'user','content':text}])
    connection=http.client.HTTPSConnection(MISTRAL_HOST,timeout=MISTRAL_TIMEOUT_SECONDS)
    try:
        connection.request('POST','/v1/chat/completions',body=canonical_json(payload).encode(),
                           headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        response=connection.getresponse()
        if response.status!=200: raise ValueError('mistral_http_request_refused')
        raw=response.read(MAX_MODEL_RESPONSE_BYTES+1)
        if len(raw)>MAX_MODEL_RESPONSE_BYTES: raise ValueError('mistral_response_exceeds_limit')
        envelope=json.loads(raw)
        if not isinstance(envelope,dict) or not isinstance(envelope.get('choices'),list) or not envelope['choices']:
            raise ValueError('mistral_transport_or_response_invalid')
        choice=envelope['choices'][0]
        if not isinstance(choice,dict) or not isinstance(choice.get('message'),dict) or not isinstance(choice['message'].get('content'),str):
            raise ValueError('mistral_transport_or_response_invalid')
        if choice.get('finish_reason')!='stop': raise ValueError('mistral_response_incomplete')
        return json.loads(choice['message']['content'])
    except (OSError, KeyError, IndexError, TypeError, ValueError, RecursionError, http.client.HTTPException) as exc:
        if type(exc) is ValueError and str(exc) in {"mistral_http_request_refused","mistral_response_exceeds_limit","mistral_response_incomplete"}:
            raise ValueError(str(exc)) from None
        raise ValueError('mistral_transport_or_response_invalid') from None
    finally:
        connection.close()


def propose(bundle, text, mapping_path, *, provider='off', replay_path=None):
    """No import or local review occurs here, even on a valid proposal."""
    try:
        if bundle.name == PUBLIC_DEMO_BUNDLE:
            from nightdesk.demo import demo_input
            if provider != 'replay':
                raise ValueError('demo_replay_only')
            if replay_path is None:
                raise ValueError('replay_path_required')
            demo_input(bundle, mapping_path, kind={"text_mapping"})
            demo_input(bundle, replay_path, kind={"replay"})
        check_input(mapping_path,bundle)
        mapping,sha=load_mapping(mapping_path)
        if mapping.record!='WorkNotice': raise ValueError('text_requires_work_mapping')
        text_guard(text)
        if provider=='off': raise ValueError('model_provider_off')
        if provider=='replay':
            if replay_path is None: raise ValueError('replay_path_required')
            proposal=cache.replay(bundle,replay_path,text,mapping.dataset,mapping.licence)
        elif provider=='mistral':
            if not mapping.external_processing_allowed: raise ValueError('dataset_external_processing_disabled')
            if not allowed(bundle): raise ValueError('bundle_external_processing_disabled')
            if not any(e.kind=='mapping_confirmed' and e.payload.get('mapping_sha256')==sha for e in read_events(bundle)):
                raise ValueError('mapping_confirmation_required')
            proposal=_send(text)
            cache.save(bundle,text,proposal,dataset=mapping.dataset,licence=mapping.licence)
        else: raise ValueError('unknown_model_provider')
        payload,reasons=validate_proposal(bundle,text,proposal,dataset=mapping.dataset,licence=mapping.licence,mode=provider,default_timezone=mapping.timezone)
        append_event(bundle,'text_proposal_checked',{'dataset':mapping.dataset,'provider':provider,'accepted':not reasons,
            'reasons':reasons,'prompt_version':PROMPT_VERSION,'source_sha256':hashlib.sha256(text.encode()).hexdigest()})
        return {'proposal':Proposal.model_validate(proposal).model_dump() if not reasons else None,
                'accepted':not reasons,'reasons':reasons,'cache_is_local':True}
    except (ValueError,OSError,TypeError,RecursionError) as exc:
        # Errors contain static codes only; transport never exposes response text/key.
        known={'mistral_key_unavailable','mistral_key_invalid_format','mistral_http_request_refused',
            'mistral_response_exceeds_limit','mistral_response_incomplete','mistral_transport_or_response_invalid',
            'text_requires_work_mapping','model_provider_off','replay_path_required','dataset_external_processing_disabled',
            'bundle_external_processing_disabled','mapping_confirmation_required','unknown_model_provider',
            'notice_empty_or_exceeds_technical_limit','text_addresses_model','nda_replay_requires_own_bundle_cache',
            'replay_input_mismatch','cache_bundle_or_hash_mismatch','cache_audit_evidence_missing',
            'replay_requires_public_or_synthetic_inputs','replay_dataset_mismatch','replay_proposal_invalid',
            'demo_replay_only','demo_input_not_manifest_listed','demo_asset_hash_mismatch','demo_asset_kind_mismatch'}
        reason=str(exc) if type(exc) is ValueError and str(exc) in known else 'text_input_or_response_invalid'
        append_event(bundle,'text_request_refused',{'provider':provider,'reason':reason})
        return {'proposal':None,'accepted':False,'reasons':[reason]}
