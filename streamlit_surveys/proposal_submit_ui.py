"""Submission UI: disable while saving and acknowledge only successful writes."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
from zoneinfo import ZoneInfo

import streamlit as st


def render_submit(payload, complete, save):
    signature = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    target = (payload['reviewer'], payload['section'], payload['group'])
    state = st.session_state.setdefault('proposal_save_ui', {
        'pending': None, 'saved': {}, 'error': None,
    })
    receipt = state['saved'].get(target)
    unchanged = receipt is not None and receipt['signature'] == signature

    def queue():
        # A second queued click cannot schedule another write of the same review.
        current = state['saved'].get(target)
        if state['pending'] is None and not (current and current['signature'] == signature):
            state['pending'] = (target, signature, deepcopy(payload))
            state['error'] = None

    busy = state['pending'] is not None
    label = 'Saving evaluation…' if busy else ('Evaluation saved' if unchanged else 'Submit Feedback')
    st.button(label, key='proposal_submit', disabled=busy or unchanged or not complete,
              on_click=queue)
    if state['error'] and state['error'][0] == target:
        st.error(state['error'][1])
    if receipt:
        if unchanged:
            st.success(f"Evaluation saved for {payload['group']} at {receipt['time']} Central. "
                       'Your group scores, individual scores, and feedback were saved. '
                       'You can select the next group, or edit this evaluation and submit a replacement.')
        else:
            st.info('You have unsaved changes. Submit Feedback will replace your previous evaluation.')
    if busy:
        pending_target, pending_signature, pending_payload = state['pending']
        try:
            with st.spinner('Saving your evaluation. Please wait…'):
                save(pending_payload)
        except ValueError as exc:
            state['error'] = (pending_target, str(exc))
        except Exception:
            state['error'] = (pending_target,
                'Save could not be confirmed. Your answers are still here. Please retry; '
                'a retry replaces this evaluation rather than adding a duplicate.')
        else:
            state['saved'][pending_target] = {
                'signature': pending_signature,
                'time': datetime.now(ZoneInfo('America/Chicago')).strftime('%I:%M:%S %p'),
            }
        finally:
            state['pending'] = None
        st.rerun()
