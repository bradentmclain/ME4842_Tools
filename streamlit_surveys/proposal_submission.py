"""Authorization and atomic replacement for the legacy presentation survey."""
from copy import deepcopy
from math import isfinite
from secrets import choice
from time import time
from uuid import uuid4

DOMAINS = {'umsystem.edu', 'mst.edu', 'missouri.edu', 'umkc.edu', 'umsl.edu'}
GROUP_FIELDS = ('technical_content_score', 'experimental_efficacy_score',
                'completeness_score', 'presentation_quality_score', 'answering_questions_score')
INDIVIDUAL_FIELDS = ('dress_code_score', 'audience_engagement_score',
                     'body_language_score', 'enthusiasm_score', 'overall_score')
RATINGS = {'Substandard', 'Poor', 'Acceptable', 'Good', 'Excellent'}


def authorized_actor(claims, students, instructors):
    email = str(claims.get('email', '')).strip().casefold()
    if claims.get('email_verified') is not True or email.rpartition('@')[2] not in DOMAINS:
        raise ValueError('A verified registered university email is required.')
    if email in instructors:
        return dict(instructors[email], role='faculty', email=email)
    if email in students:
        return dict(students[email], role='student', email=email)
    raise ValueError('Your email is not in the registered course roster.')


def validate_submission(actor, section, group, groups, group_scores, individual_scores):
    if actor['role'] != 'faculty' and actor.get('section') != section:
        raise ValueError('Students may evaluate only their registered section.')
    members = groups.get(section, {}).get(group)
    if not members or len(members) != len(set(members)):
        raise ValueError('Select a valid group in the authorized section.')
    if sorted(row.get('student_being_reviewed', '') for row in individual_scores) != sorted(members):
        raise ValueError('Complete one individual evaluation for every presenter.')
    if group_scores.get('student_being_reviewed') != members:
        raise ValueError('The group roster changed. Reload the survey before submitting.')
    for field in GROUP_FIELDS:
        value = group_scores.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or not 0 <= value <= 10:
            raise ValueError('Complete every group score using a value from 0 to 10.')
    for row in individual_scores:
        if any(row.get(field) not in RATINGS for field in INDIVIDUAL_FIELDS):
            raise ValueError('Complete every individual score before submitting.')
    return members


def replace_records(existing, group, members, payloads, candidate_keys):
    """Pure transaction callback; reuse push IDs and leave other groups untouched."""
    current = deepcopy(existing or {})
    former_members = set(members)
    for row in current.values():
        if row.get('response_type') == 'Group' and row.get('group_being_scored') == group:
            former_members.update(row.get('student_being_reviewed', []))
    matching = {}
    for key, row in list(current.items()):
        kind = row.get('response_type')
        belongs = (kind == 'Group' and row.get('group_being_scored') == group) or (
            kind == 'Individual' and (row.get('group_being_scored') == group or (
                not row.get('group_being_scored') and row.get('student_being_reviewed') in former_members)))
        if belongs:
            target = (kind, group if kind == 'Group' else row.get('student_being_reviewed'))
            matching.setdefault(target, []).append(key)
            del current[key]
    for row, candidate in zip(payloads, candidate_keys):
        target = (row['response_type'], group if row['response_type'] == 'Group' else row['student_being_reviewed'])
        key = min(matching[target]) if target in matching else candidate
        current[key] = deepcopy(row)
    return current


def new_push_key(timestamp_ms):
    # Compatible Firebase push-ID timestamp and 72 random bits, with no remote write.
    alphabet = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'
    prefix = []
    for _ in range(8):
        prefix.append(alphabet[timestamp_ms % 64])
        timestamp_ms //= 64
    return ''.join(reversed(prefix)) + ''.join(choice(alphabet) for _ in range(12))


def save_evaluation(ref, actor, section, group, groups, group_scores, individual_scores):
    members = validate_submission(actor, section, group, groups, group_scores, individual_scores)
    stamp = int(time() * 1000)
    batch = uuid4().hex
    weight = 3 if actor['role'] == 'faculty' else 1
    payloads = []
    for row, kind in [(group_scores, 'Group')] + [(row, 'Individual') for row in individual_scores]:
        payload = deepcopy(row)
        payload.update(active_user=actor['name'], response_type=kind, scoring_weight=weight,
                       group_being_scored=group, section=section, submitted_at_ms=stamp,
                       submission_id=batch)
        payloads.append(payload)
    # Allocate keys without writes; transaction retries have no side effects.
    candidates = [new_push_key(stamp) for _ in payloads]
    ref.transaction(lambda current: replace_with_history(
        current, group, members, payloads, candidates, batch, stamp, actor))


def replace_with_history(existing, group, members, payloads, candidates, batch, stamp, actor):
    """Latest records and immutable submission snapshots commit together or not at all."""
    before = deepcopy(existing or {})
    history = {}
    previous_members = set(members)
    for row in before.values():
        if row.get('response_type') == 'Group' and row.get('group_being_scored') == group:
            previous_members.update(row.get('student_being_reviewed', []))
            history.update(deepcopy(row.get('submission_history', {})))
    previous = {}
    for key, row in before.items():
        belongs = row.get('group_being_scored') == group or (
            row.get('response_type') == 'Individual' and not row.get('group_being_scored')
            and row.get('student_being_reviewed') in previous_members)
        if belongs:
            previous[key] = {k: deepcopy(v) for k, v in row.items() if k != 'submission_history'}
    if not history and previous:
        # Preserve the last pre-audit state, including legacy duplicates, without
        # pretending its migration time was the original submission time.
        history['baseline'] = {'kind': 'pre_history_snapshot',
                               'preserved_at_ms': {'.sv': 'timestamp'}, 'records': previous}
    after = replace_records(before, group, members, payloads, candidates)
    saved = {k: deepcopy(v) for k, v in after.items() if v.get('submission_id') == batch}
    for row in saved.values():
        row['received_at_ms'] = {'.sv': 'timestamp'}
    # Store the server receipt on each latest row and on its immutable batch.
    for key in saved:
        after[key]['received_at_ms'] = {'.sv': 'timestamp'}
    history[batch] = {'kind': 'submission', 'submitted_at_ms': stamp,
                      'received_at_ms': {'.sv': 'timestamp'},
                      'evaluator_email': actor.get('email', ''), 'evaluator_role': actor['role'],
                      'records': saved}
    group_row = next(v for v in after.values() if v.get('response_type') == 'Group'
                     and v.get('group_being_scored') == group)
    group_row['submission_history'] = history
    return after
