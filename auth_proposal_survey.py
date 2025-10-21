import streamlit as st
import time
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from collections import defaultdict
import random
import firebase_admin
from firebase_admin import credentials, db
import numpy as np

# =========================
# AUTH CONFIG
# =========================
ALLOWED_EMAILS = {
    "you@mst.edu",
    "ta1@mst.edu",
    "btmywv@umsystem.edu",
}

def is_allowed(email: str) -> bool:
    return bool(email) and email.lower() in {e.lower() for e in ALLOWED_EMAILS}

def login_screen():
    st.header("🔒 This app is private.")
    st.subheader("Please log in with your organization account.")
    # Streamlit's built-in OIDC login button (Google, Microsoft, Okta, etc.)
    st.button("Log in with Google", type="primary", use_container_width=True, on_click=st.login)
    with st.expander("Troubleshooting", expanded=False):
        st.write(
            "- If the login page opens in a new tab, complete the flow and return here.\n"
            "- If nothing happens, check pop-up blockers or try refreshing the page."
        )

def logout_bar(email: str | None):
    col1, col2 = st.columns([1, 1])
    with col1:
        st.caption(f"Signed in as: **{email or 'unknown'}**")
    with col2:
        st.button("Log out", use_container_width=True, on_click=st.logout)

# =========================
# APP CONTENT (PROTECTED)
# =========================
def init_firebase():
    # Only initialize once
    if not firebase_admin._apps:
        cred_dict = dict(st.secrets["firebase_creds"])
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(
            cred,
            {"databaseURL": "https://fs2025-me4842-default-rtdb.firebaseio.com/"},
        )

def protected_app():
    # --- Persisted UI state defaults (avoid KeyErrors) ---
    st.session_state.setdefault("active_user", "Click to Select")
    st.session_state.setdefault("active_section", "Click to Select")
    st.session_state.setdefault("active_group", "Click to Select")
    st.session_state.setdefault("dialog_completed", False)

    # --- Import student data from secrets (TOML list of "section, group, name") ---
    nested = defaultdict(lambda: defaultdict(list))
    for entry in st.secrets["class_list"]["students"]:
        section, group, name, email = entry.split(",", 2)
        nested[section.strip()][group.strip()].append(name.strip())

    students_by_section_group = {s: dict(groups) for s, groups in nested.items()}
    students_by_section = {
        section: [student for group in groups.values() for student in group]
        for section, groups in students_by_section_group.items()
    }

    # --- Submission dialog ---
    @st.dialog("Feedback submitted!")
    def show_review_prompt():
        # Use safe split for first name extraction
        first = (st.session_state.get("active_user") or "").split(" ")[0] or "Student"
        st.success(f"Thanks for your feedback {first}!")
        st.write("Would you like to review another group? If so, please select **Review Again** below. Otherwise, you may now close the survey.")
        if st.button("Review Again"):
            st.session_state["review_more_dialog"] = "Yes"
            st.session_state.dialog_completed = True
            st.rerun()

    # If user requests to review another, clear scoped state and restart
    if st.session_state.dialog_completed and st.session_state.get("review_more_dialog") == "Yes":
        keys_to_clear = [
            key for key in st.session_state
            if key.startswith("ind_") or key.startswith("group_") or key.startswith("selected_")
        ]
        for key in keys_to_clear:
            del st.session_state[key]
        st.session_state["active_group"] = "Click to Select"
        st.session_state.dialog_completed = False
        st.rerun()

    # --- Firebase init & DB ref ---
    init_firebase()
    ref = db.reference("Proposal_Response")

    # --- UI ---
    st.title("ME4842 Proposal Presentation Feedback")
    st.header("Student Identification")

    ind_scores = []
    group_scores = []
    weight = random.choice([1, 2])

    # Student identification (sequential)
    section = st.selectbox(
        "Select your section",
        options=["Click to Select"] + sorted(list(students_by_section.keys())),
        key="active_section"
    )

    if st.session_state["active_section"] != "Click to Select":
        st.selectbox(
            "Select your name",
            options=["Click to Select"] + students_by_section[st.session_state["active_section"]],
            key="active_user"
        )

    # Group selection
    st.header("Presentation Review")
    if st.session_state["active_section"] != "Click to Select":
        st.selectbox(
            "Select the group that is presenting",
            options=["Click to Select"] + sorted(list(students_by_section_group[st.session_state["active_section"]].keys())),
            key="active_group",
            index=0
        )

    ready = (
        st.session_state["active_section"] != "Click to Select" and
        st.session_state["active_user"]   != "Click to Select" and
        st.session_state["active_group"]  != "Click to Select"
    )

    if ready:
        st.markdown("Use this to visually track who is presenting in which order.")

        students = students_by_section_group[st.session_state["active_section"]][st.session_state["active_group"]]
        orders = [1, 2, 3, 4]

        # Initialize selection state for each student row
        for sname in students:
            st.session_state.setdefault(f"selected_{sname}", None)

        # Grid header
        cols = st.columns(len(orders) + 1)
        cols[0].markdown(" ")  # Empty top-left
        for i, order in enumerate(orders):
            cols[i + 1].markdown(f"**{order}**")

        # Grid body
        for sname in students:
            cols = st.columns(len(orders) + 1)
            cols[0].markdown(f"**{sname}**")
            for i, order in enumerate(orders):
                key = f"{sname}-{order}"
                selected_key = f"selected_{sname}"
                is_selected = st.session_state[selected_key] == order
                label = "🔘" if is_selected else "◯"
                if cols[i + 1].button(label, key=key):
                    st.session_state[selected_key] = order

        # Individual survey
        individual_responses = ["Substandard", "Poor", "Acceptable", "Good", "Excellent"]
        for sname in students:
            st.subheader(f"**Score {sname}:**")
            dress_code = st.radio("**Dress Code**", individual_responses, key=f"ind_dress_{sname}", index=0)
            audience_engagement = st.radio("**Audience Engagement**", individual_responses, key=f"ind_audience_engagement_{sname}", index=0)
            body_language = st.radio("**Body Language**", individual_responses, key=f"ind_body_language_{sname}", index=0)
            enthusiasm = st.radio("**Enthusiasm**", individual_responses, key=f"ind_enthusiasm_{sname}", index=0)
            overall = st.radio("**Speaking**", individual_responses, key=f"ind_speaking_{sname}", index=0)
            comments = st.text_area(f"**Individual feedback for {sname} (optional):**", key=f"ind_feedback_{sname}")

            ind_feedback_dict = {
                "response_type": "Individual",
                "active_user": st.session_state["active_user"],
                "scoring_weight": weight,
                "student_being_reviewed": sname,
                "dress_code_score": dress_code,
                "audience_engagement_score": audience_engagement,
                "body_language_score": body_language,
                "enthusiasm_score": enthusiasm,
                "overall_score": overall,
                "written_feedback": comments,
            }
            ind_scores.append(ind_feedback_dict)

        # Group survey
        group_id = st.session_state["active_group"]
        st.subheader(f"**Score {group_id}:**")
        group_comments = st.text_area(
            f"**Provide written overall feedback and presentation comments for {group_id} here (optional):**",
            key=f"group_feedback_{group_id}"
        )
        group_technical = st.number_input("**Overall technical content.** Did the group provide enough information for the audience to understand the topic? (0-10)",
                                          key=f"group_technical_{group_id}", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
        group_efficacy = st.number_input("**Overall efficacy of experimental plan.** Did the group convince you they will complete the experiment and achieve good results? (0-10)",
                                         key=f"group_efficacy_{group_id}", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
        group_completeness = st.number_input("**Overall completeness of proposal.** Did they leave out important information? Did they propose instrumentation details?",
                                             key=f"group_completeness_{group_id}", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
        group_presentation_quality = st.number_input("**Overall presentation quality.** Speaking clarity, slide quality, visual aids (0-10)",
                                                     key=f"group_presentation_quality_{group_id}", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")
        group_answer_questions = st.number_input("**Overall ability to answer questions.** Teamwork in Q&A (0-10)",
                                                 key=f"group_answer_questions_{group_id}", min_value=0.0, max_value=10.0, step=0.1, format="%.1f")

        group_feedback_dict = {
            "response_type": "Group",
            "active_user": st.session_state["active_user"],
            "scoring_weight": weight,
            "student_being_reviewed": students,  # list of names
            "group_being_scored": group_id,
            "written_feedback": group_comments,
            "technical_content_score": group_technical,
            "experimental_efficacy_score": group_efficacy,
            "completeness_score": group_completeness,
            "presentation_quality_score": group_presentation_quality,
            "answering_questions_score": group_answer_questions,
        }

        if st.button("Submit Feedback", type="primary"):
            ref.push(group_feedback_dict)
            for ind_response in ind_scores:
                ref.push(ind_response)
            show_review_prompt()

# =========================
# ENTRYPOINT WITH AUTH GATE
# =========================
# New Streamlit User API (dict-like), see docs:
# - st.login() redirects to your OIDC provider and back
# - st.user.is_logged_in indicates session login state
# - st.logout() clears session and identity cookie
# Docs: https://docs.streamlit.io/develop/api-reference/user
try:
    if getattr(st.user, "is_logged_in", False):
        # Safely extract from dict-like st.user
        user_email = dict(st.user).get("email")
        user_name = dict(st.user).get("name", "User")

        if is_allowed(user_email):
            logout_bar(user_email)
            st.success(f"You are successfully logged in, {user_name}.")
            protected_app()
        else:
            st.error(f"Access denied for {user_email or 'unknown user'}.")
            st.button("Log out", on_click=st.logout)
    else:
        login_screen()

except AttributeError:
    # If running on an older Streamlit with no st.user/st.login support,
    # show a helpful message instead of crashing.
    st.error(
        "This app expects Streamlit's built-in authentication (`st.login`, `st.user`). "
        "Your current environment doesn't expose these. Please upgrade Streamlit "
        "to v1.42+ and ensure your OIDC provider is configured in `secrets.toml`."
    )
