"""Shared acceptance gate; only the instructor's backend changes this node."""
CONTROL_NODE = 'Proposal_Control'


def is_accepting(value):
    # An absent control preserves the existing survey behavior; malformed settings fail closed.
    return value is None or (isinstance(value, dict) and value.get('accepting') is True)


def require_accepting(reference):
    if not is_accepting(reference.get()):
        raise ValueError('Evaluations are closed by the instructor. Your answers have not been saved.')


def save_if_accepting(reference, save, *args, **kwargs):
    require_accepting(reference)
    return save(*args, **kwargs)
