import importlib.util
from pathlib import Path
from copy import deepcopy
import pytest

spec = importlib.util.spec_from_file_location('submission', Path(__file__).parents[1] / 'streamlit_surveys/proposal_submission.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
STUDENTS = {'a@umsystem.edu': {'name': 'Student A', 'section': '301'}}
FACULTY = {'teacher@mst.edu': {'name': 'Teacher'}}
GROUPS = {'301': {'301A': ['Presenter A', 'Presenter B']}, '302': {'302A': ['Presenter C']}}


def payloads():
    group = dict(student_being_reviewed=['Presenter A', 'Presenter B'], **{f: 7 for f in s.GROUP_FIELDS})
    inds = [dict(student_being_reviewed=p, **{f: 'Good' for f in s.INDIVIDUAL_FIELDS}) for p in group['student_being_reviewed']]
    return group, inds


class Ref:
    def __init__(self): self.data = {}; self.count = 0
    def push(self):
        raise AssertionError('Key allocation must never write placeholder records')
    def transaction(self, callback):
        first = callback(deepcopy(self.data))
        assert first == callback(deepcopy(self.data))  # retry-safe
        self.data = first


def test_exact_verified_email_required():
    assert s.authorized_actor({'email':' A@UMSYSTEM.EDU ', 'email_verified':True}, STUDENTS, FACULTY)['role']=='student'
    for email, verified in [('a@mst.edu',True),('other@umsystem.edu',True),('a@umsystem.edu',False),('a@umsystem.edu',None)]:
        with pytest.raises(ValueError): s.authorized_actor({'email':email,'email_verified':verified},STUDENTS,FACULTY)


def test_section_and_completeness_enforced_before_write():
    actor = dict(STUDENTS['a@umsystem.edu'],role='student');g,i=payloads();r=Ref()
    for section,group,inds in [('302','302A',i),('301','missing',i),('301','301A',i[:1]),('301','301A',i+i[:1])]:
        with pytest.raises(ValueError): s.save_evaluation(r,actor,section,group,GROUPS,g,inds)
    assert r.count==0 and r.data=={}
    i[0]['overall_score']=None
    with pytest.raises(ValueError):s.save_evaluation(r,actor,'301','301A',GROUPS,g,i)


def test_repeat_replaces_all_scores_and_preserves_other_groups():
    actor=dict(FACULTY['teacher@mst.edu'],role='faculty');g,i=payloads();r=Ref()
    r.data={'other':{'response_type':'Group','group_being_scored':'302A','student_being_reviewed':['Presenter C']}}
    s.save_evaluation(r,actor,'301','301A',GROUPS,g,i)
    keys=set(r.data);first_batch=r.data[next(k for k in keys if k!='other')]['submission_id']
    g['technical_content_score']=9;i[0]['overall_score']='Excellent'
    s.save_evaluation(r,actor,'301','301A',GROUPS,g,i)
    assert set(r.data)==keys and len(r.data)==4
    assert r.data['other']['group_being_scored']=='302A'
    own=[row for k,row in r.data.items() if k!='other']
    assert len({row['submission_id'] for row in own})==1
    assert all(row['submission_id']!=first_batch for row in own)
    assert next(row for row in own if row['response_type']=='Group')['technical_content_score']==9
    assert next(row for row in own if row['student_being_reviewed']=='Presenter A')['overall_score']=='Excellent'


def test_legacy_duplicates_are_replaced_and_removed_members_do_not_linger():
    old={'1':{'response_type':'Group','group_being_scored':'301A','student_being_reviewed':['Old Member']},
         '2':{'response_type':'Group','group_being_scored':'301A','student_being_reviewed':['Old Member']},
         '3':{'response_type':'Individual','student_being_reviewed':'Old Member'},
         '4':{'response_type':'Individual','student_being_reviewed':'Other Member','group_being_scored':'302A'}}
    new=[{'response_type':'Group','group_being_scored':'301A','student_being_reviewed':['New Member']},
         {'response_type':'Individual','group_being_scored':'301A','student_being_reviewed':'New Member'}]
    out=s.replace_records(old,'301A',['New Member'],new,['5','6'])
    assert set(out)=={'1','4','6'} and out['4']==old['4']


def test_key_generation_is_push_id_compatible_and_unique():
    alphabet = '-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz'
    stamp = 1791830000000
    keys = {s.new_push_key(stamp) for _ in range(100)}
    assert len(keys) == 100
    for key in keys:
        decoded = 0
        for char in key[:8]: decoded = decoded * 64 + alphabet.index(char)
        assert decoded == stamp and len(key) == 20
