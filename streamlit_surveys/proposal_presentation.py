import streamlit as st
import pandas as pd
from collections import defaultdict
import firebase_admin
from firebase_admin import credentials, db
import numpy as np
from proposal_submission import authorized_actor, save_evaluation, validate_submission
from proposal_submit_ui import render_submit

if "active_section" in st.session_state:
    st.session_state.active_section = st.session_state.active_section

if "active_group" not in st.session_state:
    st.session_state.active_group = "Click to Select"
    
# persistent instructor auth state
if "instructor_verified" not in st.session_state:
    st.session_state.instructor_verified = False

# --- ADDED SIGN-IN STRUCTURE: confirmation state used by sign-in flow pattern ---
if "awaiting_confirm" not in st.session_state:
    st.session_state.awaiting_confirm = False

# --- ADDED SIGN-IN STRUCTURE: login screen function from the signed-in survey ---
def login_screen():
    st.header("This app is private.")
    st.subheader("Please log in.")
    st.button("Log in with Google", on_click=st.login)

def all_scores_filled(group_dict, individual_dicts):
    scored_filled = True

    for key in group_dict.keys():
        if key != "written_feedback":
            if group_dict[key] is None:
                scored_filled = False

    for response_dict in individual_dicts:
        for key in response_dict.keys():
            if key != "written_feedback":
                if response_dict[key] is None:
                    scored_filled = False

    return scored_filled


# --- ADDED SIGN-IN STRUCTURE: allowed-email data containers for Google sign-in access control ---
allowed_email_list = []

#import student data from toml file
nested = defaultdict(lambda: defaultdict(list))
student_dict = {}

for entry in st.secrets["class_list"]["students"]:
    section, group, name,email = entry.split(",", 3)
    section = section.strip()
    group = group.strip()
    name = name.strip()
    email = email.strip().casefold()
    email_id = email  # --- ADDED SIGN-IN STRUCTURE: store Google-login identifier ---
    allowed_email_list.append(email_id)  # --- ADDED SIGN-IN STRUCTURE: whitelist for login access ---
    if name not in nested[section][group]:
        nested[section][group].append(name)
    student_dict[email_id] = {  # --- ADDED SIGN-IN STRUCTURE: map signed-in user to survey identity ---
        "section": section,
        "group": group,
        "name": name,
        "email": email,
    }

students_by_section_group = {s: dict(groups) for s, groups in nested.items()}

students_by_section = {
    section: [student for group in groups.values() for student in group]
    for section, groups in students_by_section_group.items()
}

instructor_dict = {}

for entry in st.secrets["class_list"]["instructors"]:
    name, email = entry.split(",", 1)
    name = name.strip()
    email_id = email.strip().casefold()

    instructor_dict[email_id] = {
        "name": name
    }


# --- ADDED SIGN-IN STRUCTURE: access-check helper from the signed-in survey ---
def is_allowed(sign_in_id: str) -> bool:
    is_allowed = False
    for email_id in student_dict.keys():
        if email_id == sign_in_id:
            is_allowed = True
    return is_allowed

def is_instructor(sign_in_id: str) -> bool:
    return sign_in_id in instructor_dict

def init_firebase():
    # Only initialize once
    if not firebase_admin._apps:
        #database authentication
        cred = dict(st.secrets["firebase_creds"])
        cred = credentials.Certificate(cred)
        firebase_admin.initialize_app(cred, {"databaseURL": st.secrets['database_url']['url']})

init_firebase()
#write response to Proposal database


if st.user.is_logged_in:
    
    sign_in_dict = dict(st.user)
    sign_in_email = sign_in_dict.get("email", "").strip().casefold()
    sign_in_id = sign_in_email
    sign_in_name = sign_in_dict.get("name", "User")


    try:
        actor = authorized_actor(sign_in_dict, student_dict, instructor_dict)
    except ValueError:
        actor = None

    if actor is not None:
        
        st.success(f"You are successfully logged in, {sign_in_name}.")

        ####Begin UI Here
        st.title("ME4842 Proposal Presentation Feedback")
        st.header("User Identification")

        
        

        ind_scores = []
        group_scores = []
        weight = 1

        if is_instructor(sign_in_id):
            st.session_state.instructor_verified = True
            st.session_state.active_user = instructor_dict[sign_in_id]["name"]
            weight = 3
            st.markdown(f'#### Your Name: :green[{st.session_state["active_user"]}]')
            st.markdown(f'#### Section: :green[Instructor]')

            #user identification, must be sequential
            section_dropdown = st.selectbox(
                "Select the section that is presenting",
                options=["Click to Select"] + sorted(students_by_section),
                key='active_section'
            )
        else:
            st.session_state.active_section = student_dict[sign_in_id]['section']
            st.session_state.active_user = student_dict[sign_in_id]['name']
            st.markdown(f'#### Name: :green[{st.session_state["active_user"]}]')
            st.markdown(f'#### Section: :green[{st.session_state["active_section"]}]')
        ref = db.reference(f"Proposal_Responses/{st.session_state['active_user']}")
        #Select group to review

        st.header("Presentation Review")
        st.info("Submitting again for the same group replaces your previous group and individual evaluations. Your evaluations of other groups are kept.")
        # A section change or refreshed roster must not leave a stale group selected.
        available_groups = students_by_section_group.get(st.session_state['active_section'], {})
        if st.session_state.get('active_group') not in available_groups:
            st.session_state['active_group'] = 'Click to Select'
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
                try:
                    validate_submission(actor, st.session_state.active_section,
                                        st.session_state.active_group, students_by_section_group,
                                        group_feedback_dict, ind_scores)
                    is_complete = True
                except ValueError:
                    is_complete = False
                #on data submission
                if not is_complete:
                    st.write('Please complete all required fields before submitting.')
                def save_pending(payload):
                    # Recheck identity and section at the write boundary.
                    current_actor = authorized_actor(dict(st.user), student_dict, instructor_dict)
                    if current_actor['name'] != payload['reviewer']:
                        raise ValueError('Your sign-in changed. Reload before submitting.')
                    save_evaluation(ref, current_actor, payload['section'], payload['group'],
                                    students_by_section_group, payload['group_scores'],
                                    payload['individual_scores'])

                render_submit({
                    'reviewer': actor['name'],
                    'section': st.session_state.active_section,
                    'group': st.session_state.active_group,
                    'group_scores': group_feedback_dict,
                    'individual_scores': ind_scores,
                }, is_complete, save_pending)

    else:
        st.error(f"Access denied for {sign_in_id or 'unknown user'}.")
        st.button("Log out", on_click=st.logout)
else:
    login_screen()