"""Authorization and atomic replacement for the legacy presentation survey."""
from copy import deepcopy
from math import isfinite
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
    candidates = [ref.push().key for _ in payloads]
    ref.transaction(lambda current: replace_records(current, group, members, payloads, candidates))
