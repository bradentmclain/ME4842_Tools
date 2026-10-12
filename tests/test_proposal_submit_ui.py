from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = str(Path(__file__).resolve().parents[1] / 'streamlit_surveys')
APP = '''
import sys
sys.path.insert(0, ROOT)
import streamlit as st
from proposal_submit_ui import render_submit
score = st.number_input('Score', value=5)
fail = st.checkbox('Simulate save failure')
complete = st.checkbox('Complete', value=True)
st.session_state.setdefault('writes', 0)
st.session_state.setdefault('attempts', 0)
original_button = st.button
def tracked_button(*args, **kwargs):
    st.session_state['disabled_at_render'] = kwargs.get('disabled')
    st.session_state['label_at_render'] = args[0]
    return original_button(*args, **kwargs)
st.button = tracked_button
try:
    def save(payload):
        assert st.session_state['disabled_at_render'] is True
        assert st.session_state['label_at_render'] == 'Saving evaluation…'
        st.session_state['attempts'] += 1
        if fail:
            raise RuntimeError('Synthetic failure')
        st.session_state['writes'] += 1
        st.session_state['saved_score'] = payload['score']
    render_submit({'reviewer':'Test', 'section':'TEST', 'group':'TEST ONLY', 'score':score}, complete, save)
finally:
    st.button = original_button
'''.replace('ROOT', repr(ROOT))


def test_busy_confirmation_and_no_repeat_until_edit():
    app = AppTest.from_string(APP).run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['writes'] == 1
    assert app.button[0].disabled
    assert app.button[0].label == 'Evaluation saved'
    assert 'Evaluation saved for TEST ONLY' in app.success[0].value
    # Even a queued second click after success must not write twice.
    app.button[0].click().run()
    assert app.session_state['writes'] == 1
    app.number_input[0].set_value(8).run()
    assert not app.button[0].disabled
    assert not app.success
    app.button[0].click().run()
    assert app.session_state['writes'] == 2
    assert app.session_state['saved_score'] == 8


def test_failure_preserves_answers_and_reenables_retry():
    app = AppTest.from_string(APP).run()
    app.checkbox[0].check().run()
    app.button[0].click().run()
    assert not app.exception
    assert app.session_state['writes'] == 0
    assert app.error and not app.success
    assert not app.button[0].disabled
    assert app.number_input[0].value == 5
    app.checkbox[0].uncheck().run()
    app.button[0].click().run()
    assert app.session_state['writes'] == 1
    assert app.success and not app.error


def test_incomplete_disabled():
    app = AppTest.from_string(APP).run()
    app.checkbox[1].uncheck().run()
    assert app.button[0].disabled
    assert app.session_state['attempts'] == 0
