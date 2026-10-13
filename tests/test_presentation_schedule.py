from streamlit_surveys.proposal_schedule import apply_presentation_schedule, presentation_section


def test_move_only_presentation_session_preserving_originals():
    groups = {"301": {"301A": ["Host"]}, "309": {"309D": ["Visitor"], "309A": ["Other"]}}
    students = {
        "v@mst.edu": {"name": "Visitor", "section": "309", "group": "309D"},
        "o@mst.edu": {"name": "Other", "section": "309", "group": "309A"},
    }
    moved, actors = apply_presentation_schedule(groups, students)
    assert moved["301"]["309D"] == ["Visitor"]
    assert "309D" not in moved["309"]
    assert moved["309"]["309A"] == ["Other"]
    assert actors["v@mst.edu"]["section"] == "301"
    assert actors["v@mst.edu"]["registered_section"] == "309"
    assert actors["o@mst.edu"]["section"] == "309"
    assert students["v@mst.edu"]["section"] == "309"
    assert groups["309"]["309D"] == ["Visitor"]
    assert apply_presentation_schedule(moved, actors) == (moved, actors)
    assert presentation_section("309D") == "301"


def test_host_section_can_evaluate_visiting_group_but_other_sections_cannot():
    import pytest
    from streamlit_surveys.proposal_submission import validate_submission, GROUP_FIELDS, INDIVIDUAL_FIELDS
    groups, _ = apply_presentation_schedule({'301':{'301A':['Host']}, '309':{'309D':['Visitor']}}, {})
    gs = dict.fromkeys(GROUP_FIELDS,5)
    gs['student_being_reviewed']=['Visitor']
    individual = dict.fromkeys(INDIVIDUAL_FIELDS,'Good')
    individual['student_being_reviewed']='Visitor'
    assert validate_submission({'role':'student','section':'301'},'301','309D',groups,gs,[individual]) == ['Visitor']
    with pytest.raises(ValueError):
        validate_submission({'role':'student','section':'309'},'301','309D',groups,gs,[individual])
