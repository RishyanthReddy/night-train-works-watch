"""Delay requests have no validated prediction method."""
from nightdesk.model import Refusal


def estimate_delay(*args, **kwargs) -> Refusal:
    return Refusal(reason_code='prediction_not_validated',
        detail='Delay prediction is unavailable. Works exposure and boundary checks do not establish a delay.',
        what_would_fix_it='A written prediction method validated on suitable evidence and explicitly approved by the user.')
