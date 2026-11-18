"""Source-quoted WorkNotice proposals; file/manual/model share typed gates."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from nightdesk.audit import append_event, canonical_json
from nightdesk.config import MAX_NOTICE_CHARS, TEXT_INJECTION_MARKERS, TEXT_INJECTION_PATTERNS, TEXT_MONTHS
from nightdesk.gates import typed_record
from nightdesk.model import GenericRow, SourceRef, WorkNotice, JSONValue
from nightdesk.intake.mapping import load_mapping, write_private, confirm_mapping, ingest, check_input


class Proposal(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    fields: dict[str, JSONValue]
    quotes: dict[str, str]


def text_guard(text):
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_NOTICE_CHARS:
        raise ValueError('notice_empty_or_exceeds_technical_limit')
    normalized = unicodedata.normalize('NFKC', text).casefold()
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Cf')
    normalized = ' '.join(normalized.split())
    if any(marker in normalized for marker in TEXT_INJECTION_MARKERS) or any(re.search(pattern,normalized) for pattern in TEXT_INJECTION_PATTERNS):
        raise ValueError('text_addresses_model')


def _supported(value, quote):
    if value is None: return True
    if isinstance(value, str):
        if value and value in quote: return True
        # A deterministic spelling conversion supports manually entered German dates.
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            try:
                day = datetime.strptime(value, '%Y-%m-%d')
                return day.strftime('%d.%m.%Y') in quote
            except ValueError: return False
        return value == ''
    try:
        if json.loads(quote) == value: return True
    except (ValueError, TypeError):
        pass
    return canonical_json(value) in quote


def validate_proposal(bundle, text, proposal, *, dataset, licence, mode, captured_at=None, default_timezone=None):
    """Return canonical payload and reasons; never save a revision on failure."""
    now = captured_at or datetime.now(timezone.utc)
    reasons = []
    try:
        text_guard(text)
        proposal = Proposal.model_validate(proposal)
        allowed = set(WorkNotice.model_fields) - {'extra','unresolved','proposed_by'}
        if set(proposal.fields) - allowed: raise ValueError('proposal_field_not_allowed')
        present = {k:v for k,v in proposal.fields.items() if v is not None and v != ''}
        if set(proposal.quotes) != set(present): raise ValueError('field_quote_missing_or_extra')
        for name, value in present.items():
            quote = proposal.quotes[name]
            if not quote.strip() or quote not in text or not _supported(value, quote):
                raise ValueError('field_not_supported_by_quote:' + name)
        months = re.findall(r'\b(?:month|monat)(\s*[:-]\s*|\s+)([\wäöü]+)', text.casefold())
        for separator,month in months:
            if month not in TEXT_MONTHS:
                if separator.strip() in {':','-'}: raise ValueError('declared_month_unknown')
                continue  # Ordinary prose is not an explicit month declaration.
            dates = [datetime.strptime(str(proposal.fields[k]), '%Y-%m-%d').date() for k in ('date_start','date_end')]
            lo,hi=dates
            span=(hi.year-lo.year)*12+hi.month-lo.month
            if span>=0 and TEXT_MONTHS[month] not in {(lo.month-1+i)%12+1 for i in range(min(span+1,12))}:
                raise ValueError('month_contradicts_dates')
        sha = hashlib.sha256(text.encode()).hexdigest()
        source = SourceRef(bundle=bundle.name, dataset=dataset, record_id='notice', capture_id=sha,
            content_sha256=sha, captured_at=now, url_or_path='local text proposal', licence=licence,
            field_evidence=proposal.quotes)
        if proposal.fields.get('timezone'):
            from zoneinfo import ZoneInfo
            ZoneInfo(proposal.fields['timezone'])
        fields = dict(proposal.fields)
        if not fields.get('timezone') and default_timezone: fields['timezone']=default_timezone
        fields = dict(fields, proposed_by='manual' if mode == 'manual' else 'llm')
        payload, gates = typed_record(GenericRow(source=source, fields=fields), 'WorkNotice', fields.get('timezone'))
        reasons = [g.reason_code for g in gates if not g.passed]
        if payload is None or reasons: return None, reasons or ['schema_invalid']
        return payload, []
    except (ValueError, KeyError, TypeError, RecursionError, ValidationError) as exc:
        code = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, ValidationError) else 'proposal_schema_invalid'
        # Only known static messages/field names, never arbitrary Pydantic/source text.
        known = {'notice_empty_or_exceeds_technical_limit','text_addresses_model','proposal_field_not_allowed',
                 'field_quote_missing_or_extra','declared_month_unknown','month_contradicts_dates'}
        return None, [code if code in known or code.startswith('field_not_supported_by_quote:') else 'proposal_schema_invalid']


def submit_text(bundle, text, proposal, mapping_path, *, actor, mode='manual'):
    if not actor.strip(): raise ValueError('text_actor_required')
    if mode not in {'manual','llm','replay'}: raise ValueError('unknown_text_mode')
    check_input(mapping_path,bundle)
    mapping, _ = load_mapping(mapping_path)
    if mapping.record != 'WorkNotice': raise ValueError('text_requires_work_mapping')
    payload, reasons = validate_proposal(bundle,text,proposal,dataset=mapping.dataset,licence=mapping.licence,mode=mode,default_timezone=mapping.timezone)
    append_event(bundle,'text_proposal_checked',{'dataset':mapping.dataset,'actor':actor,'mode':mode,
        'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'accepted':not reasons,'reasons':reasons})
    if reasons: return {'accepted':0,'rejected':1,'reasons':reasons}
    # Preserve text and all quotes in the retained source row/extra. Import through
    # the same mapping/C1-C5/W1-W3 pipeline used for ordinary files.
    body = dict(fields=proposal['fields'], evidence=proposal['quotes'], source_text=text, actor=actor,
                drafted_by=mode, reviewed_by=actor, timezone_basis='source_field' if proposal['fields'].get('timezone') else 'declared_mapping' if mapping.timezone else 'none',
                declared_mapping_sha256=hashlib.sha256(Path(mapping_path).read_bytes()).hexdigest())
    identifier = hashlib.sha256(canonical_json([body,mode,mapping.dataset,mapping.licence]).encode()).hexdigest()
    root = bundle.resolve(bundle.root/'text'/identifier);root.mkdir(parents=True,exist_ok=True)
    fields = {}
    for name in proposal['fields']:
        parser = 'date:%Y-%m-%d' if name in {'date_start','date_end'} else 'time:%H:%M:%S' if name in {'clock_from','clock_to'} and payload.timezone else 'str'
        if name == 'weekdays': parser='list:;:int'
        fields[name]={'column':'fields.'+name,'parse':parser}
    # Canonicalise accepted temporal fields before the mapping parser, preserving
    # the person's/model's original values alongside their quotes.
    body['canonical'] = payload.model_dump(mode='json',exclude={'extra','unresolved'})
    for name in fields: fields[name]['column']='canonical.'+name
    if payload.timezone and 'timezone' not in fields: fields['timezone']={'column':'canonical.timezone','parse':'str'}
    fields['proposed_by']={'column':'canonical.proposed_by','parse':'str'}
    spec=dict(version=1,dataset=mapping.dataset,licence=mapping.licence,complete=False,
        external_processing_allowed=False,file={'type':'json'},record='WorkNotice',timezone=payload.timezone,
        required=['country','date_start','date_end'],fields=fields)
    source=root/'notice.json';spec_path=root/'mapping.yaml'
    for path, value in ((source,[body]),(spec_path,spec)):
        rendered=canonical_json(value)+'\n'
        if not path.exists(): write_private(path,rendered)
        elif path.read_text()!=rendered: raise ValueError('text_retained_content_mismatch')
    confirm_mapping(spec_path,bundle,actor)
    return ingest(source,spec_path,bundle)
