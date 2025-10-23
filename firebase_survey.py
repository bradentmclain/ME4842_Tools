import streamlit as st
import time
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from collections import defaultdict
import random
import firebase_admin
from firebase_admin import credentials, db
import numpy as np

#these should persist between sessions
if "active_user" in st.session_state:
    st.session_state.active_user = st.session_state.active_user

if "active_section" in st.session_state:
    st.session_state.active_section = st.session_state.active_section

#initialization things for UI
if "dialog_completed" not in st.session_state:
    st.session_state.dialog_completed = False

if "active_group" not in st.session_state:
    st.session_state.active_group = "Click to Select"
    
# persistent instructor auth state
if "instructor_verified" not in st.session_state:
    st.session_state.instructor_verified = False
if "instructor_name" not in st.session_state:
    st.session_state.instructor_name = "Click to Select"

def all_scores_filled(dict1,dict2):
    scored_filled = True
    for key in dict1.keys():
        if key != "written_feedback":
            if dict1[key] == None:
                scored_filled = False
    for key in dict2.keys():
        if key != "written_feedback":
            if dict2[key] == None:
                scored_filled = False
    return scored_filled


#import student data from toml file
nested = defaultdict(lambda: defaultdict(list))

for entry in st.secrets["class_list"]["students"]:
    section, group, name = entry.split(",", 2)
    section = section.strip()
    group = group.strip()
    name = name.strip()
    nested[section][group].append(name)

students_by_section_group = {s: dict(groups) for s, groups in nested.items()}

students_by_section = {
    section: [student for group in groups.values() for student in group]
    for section, groups in students_by_section_group.items()
}

# Try to load instructor list from secrets; fallback if missing
INSTRUCTOR_LIST = list(st.secrets.get("class_list", {}).get("instructors", [])) or [
    "Dr. Liou", "Dr. Wang", "Dr. McLain", "Dr. Harris"
]

#submission dialog popup
@st.dialog("Feedback submitted!")
def show_review_prompt():
    # fixed quoting inside f-string below
    st.success(f"Thanks for your feedback {st.session_state['active_user'].split(' ')[0]}!")
    st.write("Would you like to review another group? If so, please select 'Review Again' below. Otherwise, you may now close the survey.")
    if st.button("Review Again"):
        st.session_state['review_more_dialog'] = "Yes"
        st.session_state.dialog_completed = True
        st.rerun()

#if user requests to review another, launch new session. Delete old data
if st.session_state.dialog_completed and st.session_state.get("review_more_dialog") == "Yes":
    keys_to_clear = [key for key in st.session_state if (
        key.startswith("ind_") or 
        key.startswith("group_") or
        key.startswith("active_group")
    )]
    for key in keys_to_clear:
        del st.session_state[key]

    # Reset flag so this only happens once
    st.session_state.dialog_completed = False
    st.rerun()

def init_firebase():
    # Only initialize once
    if not firebase_admin._apps:
        #database authentication
        cred = dict(st.secrets["firebase_creds"])
        cred = credentials.Certificate(cred)
        firebase_admin.initialize_app(cred, {"databaseURL": "https://fs2025-me4842-default-rtdb.firebaseio.com/"})

init_firebase()
#write response to Proposal database
ref = db.reference("Proposal_Response4")

####Begin UI Here
st.title("ME4842 Proposal Presentation Feedback")
st.header("Student Identification")

ind_scores = []
group_scores = []
weight = 1

#user identification, must be sequential
section_dropdown = st.selectbox(
    "Select your section",
    options=["Click to Select"] + list(students_by_section.keys()),
    key='active_section'
)

# ------- Name selection with "I am an instructor" flow + passphrase (persistent) -------
if st.session_state['active_section'] != 'Click to Select':
    # include instructor sentinel option
    name_options = ["Click to Select"] + list(students_by_section[st.session_state['active_section']]) + ["I am an instructor"]

    chosen_name_or_role = st.selectbox("Select your name", options=name_options, key='name_choice')

    if chosen_name_or_role == "I am an instructor":
        # If already verified this session, skip passphrase
        if st.session_state.instructor_verified:
            st.success("Instructor verified (session).")
            inst_choice = st.selectbox(
                "Select your instructor name",
                options=["Click to Select"] + INSTRUCTOR_LIST,
                key='instructor_choice',
                index=(["Click to Select"] + INSTRUCTOR_LIST).index(st.session_state.instructor_name)
                if st.session_state.instructor_name in (["Click to Select"] + INSTRUCTOR_LIST) else 0
            )
            st.session_state.instructor_name = inst_choice
            st.session_state.active_user = inst_choice if inst_choice != "Click to Select" else "Click to Select"
            weight = 3
        else:
            st.info("Instructor verification required.")
            passphrase_input = st.text_input("Enter instructor passphrase", type="password", key="instructor_passphrase_input")

            # Check against secret
            correct_pass = st.secrets["class_list"].get("instructor_passphrase", None)

            if passphrase_input:
                if passphrase_input == correct_pass:
                    st.success("Passphrase verified.")
                    st.session_state.instructor_verified = True  # <-- persist across reruns
                    inst_choice = st.selectbox(
                        "Select your instructor name",
                        options=["Click to Select"] + INSTRUCTOR_LIST,
                        key='instructor_choice'
                    )
                    st.session_state.instructor_name = inst_choice
                    st.session_state.active_user = inst_choice if inst_choice != "Click to Select" else "Click to Select"
                    weight = 3
                else:
                    st.error("Incorrect passphrase.")
                    st.session_state.active_user = "Click to Select"
                    st.session_state.instructor_verified = False
                    st.session_state.instructor_name = "Click to Select"
            else:
                # No passphrase entered yet
                st.session_state.active_user = "Click to Select"
                st.session_state.instructor_name = "Click to Select"
                st.session_state.instructor_verified = False
    else:
        # Student chosen
        st.session_state.active_user = chosen_name_or_role
        # If they switch from instructor to student, keep instructor flags intact,
        # but weight remains student unless instructor mode is actively used.
        # weight stays 1 here.

# Make weight available after the block (fallback if not set above)
# try:
#     weight
# except NameError:
#     weight = 3 if st.session_state.instructor_verified else 1
# -------------------------------------------------------------------------



#Select group to review
st.header("Presentation Review")
if st.session_state['active_section'] != 'Click to Select':
    group = st.selectbox(
        "Select the group that is presenting",
        options=["Click to Select"] + sorted(list(students_by_section_group[st.session_state['active_section']].keys())),
        key='active_group',
        index=0
    )

# Only proceed with questions if student group,section, and name have been selected, make sure default is not selected
#ask questions about each student in group, create visual grid as well
if st.session_state['active_section'] != "Click to Select" and st.session_state['active_user'] != "Click to Select" and st.session_state['active_group'] != "Click to Select":
    st.markdown("Use this to visually track who is presenting in which order.")

    students = students_by_section_group[st.session_state['active_section']][group]
    orders = np.arange(1,len(students)+1)
    
    # Initialize selection state for each student row
    for student in students:
        if f"selected_{student}" not in st.session_state:
            st.session_state[f"selected_{student}"] = None  # No selection yet

    cols = st.columns(len(orders) + 1)
    cols[0].markdown(" ")  # Empty top-left
    # for i, order in enumerate(orders):
    #     cols[i + 1].markdown(f"**{order}**")

    for s in students:
        st.session_state.setdefault(f"selected_{s}", None)

    for student in students:
        col1, col2 = st.columns([1, 4])  # adjust width ratio as needed
        col1.markdown(f"**{student}**")
        col2.radio(label=f"Select for {student}",options=orders,key=f"selected_{student}",horizontal=True,label_visibility="collapsed")
    
    #individual survey questions
    individual_responses = ['Substandard',"Poor","Acceptable","Good","Excellent"]
    selected_students = []
    for order in orders:
        for student in students:
            selected_key = f"selected_{student}"
            if st.session_state.get(selected_key) == order:
                selected_students.append(student)
    if selected_students:
        for student in selected_students:
            st.subheader(f"**Score {student}:**")
            dress_code = st.radio(f"**Dress Code**", individual_responses, key=f"ind_dress_{student}",horizontal = True,index=None)
            audience_engagement = st.radio(f"**Audience Engagement**", individual_responses, key=f"ind_audience_engagement_{student}",horizontal = True,index=None)
            body_language = st.radio(f"**Body Language**", individual_responses, key=f"ind_body_language_{student}",horizontal = True,index=None)
            enthusiasm = st.radio(f"**Enthusiasm**", individual_responses, key=f"ind_enthusiasm_{student}",horizontal = True,index=None)
            overall = st.radio(f"**Speaking**", individual_responses, key=f"ind_speaking_{student}",horizontal = True,index=None)
            comments = st.text_area(f"**Individual feedback for {student} (optional):**", key=f"ind_feedback_{student}")

            ind_feedback_dict = {
                "response_type":'Individual',
                "active_user": st.session_state.active_user,
                "scoring_weight": weight,
                "student_being_reviewed": student,
                "dress_code_score": dress_code,
                "audience_engagement_score": audience_engagement,
                "body_language_score": body_language,
                "enthusiasm_score": enthusiasm,
                "overall_score": overall,
                "written_feedback": comments
            }
            ind_scores.append(ind_feedback_dict)

        #group survey question
        st.subheader(f"**Score {group}:**")
        group_comments = st.text_area(f"**Provide written overall feedback and presentation comments for {group} here (optional):**", key=f"group_feedback_{group}")
        group_technical = st.number_input(f"**Overall technical content.** Did {group} provide enough information for the audience to understand the topic? (0-10)",key=f"group_technical_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f",value=None)
        group_efficacy = st.number_input(f"**Overall efficacy of experimental plan.**  did {group} convince you that they will complete the experiment and achieve good results? (0-10)", key=f"group_efficacy_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f",value=None)
        group_completeness = st.number_input(f"**Overall completeness of proposal.** Did {group} leave out any important information? Did they propose the details of their experimental setup (i.e. specific instrumentation)?",key=f"group_completeness_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f",value=None)
        group_presentation_quality = st.number_input(f"**Overall presentation quality.** Did {group} effectively communicate their ideas? Did they speak clearly and use well made slides with good visual aids?",key=f"group_presentation_quality_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f",value=None)
        group_answer_questions = st.number_input(f"**Overall ability to answer questions.** Did {group} work well together to answer the audience and reviewer questions?",key=f"group_answer_questions_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f",value=None)

        group_feedback_dict = {
            "response_type":'Group',
            "active_user": st.session_state.active_user,
            "scoring_weight": weight,
            "student_being_reviewed": students,
            "group_being_scored": st.session_state.active_group,
            "written_feedback": group_comments,
            "technical_content_score": group_technical,
            "experimental_efficacy_score": group_efficacy,
            "completeness_score": group_completeness,
            "presentation_quality_score": group_presentation_quality,
            "answering_questions_score": group_answer_questions
        }
        is_complete = all_scores_filled(group_feedback_dict, ind_feedback_dict)
        #on data submission
        if not is_complete:
            st.write('Please complete all required fields before submitting.')
        if st.button("Submit Feedback", disabled = not is_complete):
            ref.push(group_feedback_dict)
            for ind_response in ind_scores:
                ref.push(ind_response)
            show_review_prompt()
