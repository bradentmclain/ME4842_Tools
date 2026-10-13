from types import SimpleNamespace
import pytest
from proposal_acceptance import is_accepting, save_if_accepting


def test_closed_and_malformed_controls_never_call_save():
    for value in ({'accepting': False}, {}, {'accepting': 'true'}, False):
        calls = []
        with pytest.raises(ValueError, match='closed'):
            save_if_accepting(SimpleNamespace(get=lambda: value), lambda: calls.append(1))
        assert calls == []


def test_current_state_checked_again_and_errors_fail_closed():
    state = {'accepting': True}
    ref = SimpleNamespace(get=lambda: state)
    assert is_accepting(ref.get())
    state['accepting'] = False  # instructor closes after the form was rendered
    with pytest.raises(ValueError):
        save_if_accepting(ref, lambda: pytest.fail('Must not write'))
    def broken():
        raise RuntimeError('Network unavailable')
    with pytest.raises(RuntimeError):
        save_if_accepting(SimpleNamespace(get=broken), lambda: pytest.fail('Must not write'))


def test_open_and_absent_control_allow_saving():
    for value in (None, {'accepting': True}):
        assert save_if_accepting(SimpleNamespace(get=lambda: value), lambda x: x, 42) == 42
