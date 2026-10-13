"""Exercise the real grade_prop method without Firebase/Streamlit side effects."""
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from legacy_proposal_grading import GROUP_FIELDS, INDIVIDUAL_FIELDS


def method():
    tree = ast.parse(Path('grader.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Grader')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'grade_prop')
    data = {}
    env = {'db': SimpleNamespace(reference=lambda _: SimpleNamespace(get=lambda: data)),
           'st': SimpleNamespace(secrets={'class_list': {
               'students': [f'301,301A,s{i},s{i}@mst.edu' for i in range(30)],
               'instructors': ['ta, ta@mst.edu']}})}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), 'grader.py', 'exec'), env)
    for i, name in enumerate([f's{i}' for i in range(30)] + ['ta']):
        faculty = name == 'ta'
        group = dict.fromkeys(GROUP_FIELDS, 10 if faculty else 6)
        group.update(response_type='Group', group_being_scored='301A', student_being_reviewed=['Presenter'])
        individual = dict.fromkeys(INDIVIDUAL_FIELDS, 'Excellent' if faculty else 'Substandard')
        individual.update(response_type='Individual', student_being_reviewed='Presenter')
        data[name] = {'--------' + str(i*2).zfill(12): group,
                      '--------' + str(i*2+1).zfill(12): individual}
    return env['grade_prop'], data


def test_actual_grader_cohort_formula_and_repeat_calls():
    fn, _ = method()
    grader = SimpleNamespace()
    first = fn(grader)
    # 85% individual * 20 points + 90% group * 15 points.
    assert first['Presenter'][0] == pytest.approx(30.5)
    assert 'Individual: 17.00/20' in first['Presenter'][1]
    assert 'Group: 13.50/15' in first['Presenter'][1]
    assert fn(grader) == first


def test_actual_grader_holds_missing_cohort():
    fn, data = method()
    del data['ta']
    with pytest.raises(ValueError, match='held'):
        fn(SimpleNamespace())
