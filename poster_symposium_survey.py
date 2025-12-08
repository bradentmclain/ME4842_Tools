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

if "awaiting_confirm" not in st.session_state:
	st.session_state.awaiting_confirm = False
	
def login_screen():
	st.header("This app is private.")
	st.subheader("Please log in with your university email.")
	st.button("Log in with Google", on_click=st.login)

def all_scores_filled(ind_scores):
	scored_filled = True
	for response_dict in ind_scores:
		for key in response_dict.keys():
			if response_dict[key] == None:
				scored_filled = False
	return scored_filled

#submission dialog popup
@st.dialog("Feedback submitted!")
def show_review_prompt():
    # fixed quoting inside f-string below
    st.success(f"Thanks for your feedback, {st.session_state['active_user'].split(' ')[0]}!")
    st.write("Would you like to review another group? If so, please select 'Review Again' below. Otherwise, you may now close the survey.")
    if st.button("Review Again"):
        st.session_state['review_more_dialog'] = "Yes"
        st.session_state.dialog_completed = True
        st.rerun()

#if user requests to review another, launch new session. Delete old data
if st.session_state.dialog_completed and st.session_state.get("review_more_dialog") == "Yes":
    keys_to_clear = [key for key in st.session_state if (
        key.startswith("ind_") or 
        key.startswith("active_group")
    )]
    for key in keys_to_clear:
        del st.session_state[key]

    # Reset flag so this only happens once
    st.session_state.dialog_completed = False
    st.rerun()


allowed_email_list = []

#import student data from toml file
nested = defaultdict(lambda: defaultdict(list))

student_dict = {}

for entry in st.secrets["class_list"]["students"]:
	section, group, name, emails = entry.split(",", 3)
	section = section.strip()
	group = group.strip()
	name = name.strip()
	email_id = emails.strip().split('@')[0]
	allowed_email_list.append(email_id)
	nested[section][group].append(name)
	student_dict[email_id] = {}
	student_dict[email_id]['section'] = section
	student_dict[email_id]['group'] = group
	student_dict[email_id]['name'] = name
					

def is_allowed(sign_in_id: str) -> bool:
	is_allowed = False
	domain = sign_in_id.split('@')[-1]
	if domain == 'mst.edu' or domain == 'umsystem.edu':
		is_allowed = True
	return is_allowed

students_by_section_group = {s: dict(groups) for s, groups in nested.items()}

students_by_section = {
	section: [student for group in groups.values() for student in group]
	for section, groups in students_by_section_group.items()
}


def init_firebase():
	# Only initialize once
	if not firebase_admin._apps:
		#database authentication
		cred = dict(st.secrets["firebase_creds"])
		cred = credentials.Certificate(cred)
		firebase_admin.initialize_app(cred, {"databaseURL": "https://fs2025-me4842-default-rtdb.firebaseio.com/"})

init_firebase()
#write response to Proposal database


if st.user.is_logged_in:
	# Safely extract claims (st.user is dict-like)
	sign_in_dict = dict(st.user)
	sign_in_id = sign_in_dict.get("email")
	sign_in_name = sign_in_dict.get("name", "User")

	st.session_state['active_user'] = sign_in_name

	if is_allowed(sign_in_id):
		
		st.success(f"You are successfully logged in, {sign_in_name}.")
		####Begin UI Here
		st.title("ME4842 Poster Symposium Evaluation")

		ind_scores = []

		ref = db.reference(f"Poster_Symposium_Evaluation/{st.session_state['active_user']}")

		
		all_groups = sorted({g for section_groups in students_by_section_group.values() for g in section_groups.keys()})

		group = st.selectbox("Select the group that is presenting",	options=["Click to Select"] + all_groups,key="active_group",index=0	)

		#Select group to review
		st.header("Peer Evaluation")
		if st.session_state['active_group'] != 'Click to Select':
			st.markdown(f"##### Numerical grade of **completeness**")
			completeness =  st.number_input(f"Did the group complete the experiment? Did they take measurements to identify sources of error? Should they have done more testing? (Enter a number between 0 and 100. 0 = poor and 100 = outstanding", key=f"completeness_{group}", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", value=None)
			st.markdown(f"##### Numerical grade of **technical content**")
			technical_content =  st.number_input(f"Technical content – the technical difficulty of the experiment, and quality of the technical content presented. (Enter a number between 0 and 100. 0 = poor and 100 = outstanding)", key=f"content_{group}", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", value=None)
			st.markdown(f"##### Numerical grade of **presentation quality**")
			presentation_quality =  st.number_input(f"Quality of presentation – clarity and organization of presentation in terms of layout, visual aids, and examples of hardware. (Enter a number between 0 and 100. 0 = poor and 100 = outstanding)", key=f"quality_{group}", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", value=None)
			st.markdown(f"##### Numerical grade of group's **ability to answer questions**")
			ability_to_answer_questions =  st.number_input(f"Ability to answer questions – clarity, completeness, and precision of answers to any questions regarding the presented experiment. (Enter a number between 0 and 100. 0 = poor and 100 = outstanding)", key=f"questions_{group}", min_value=0.0, max_value=100.0, step=0.1, format="%.1f", value=None)

			st.markdown(f'##### Provide any longhand feedback here.')
			feedback = st.text_area(f"If you provide feedback for individual presenters, identify them by name in your response. Things you might comment on include the following: your evaluation or interpretation of the results, speaker preparedness, elocution, and any recommendations you have for future presentations.", key=f"comments_{group}")

			ind_feedback_dict = {
				"active_user": st.session_state.active_user,
				"completeness": completeness,
				"technical_content": technical_content,
				"presentation_quality": presentation_quality,
				"answering_questions": ability_to_answer_questions,
				"feedback": feedback,
			}
			ind_scores.append(ind_feedback_dict)

			#group survey question

			is_complete = all_scores_filled(ind_scores)
			#on data submission
			if not is_complete:
				st.write('Please finish scoring before submitting.')
			if st.button("Submit Feedback", disabled = not is_complete):
				if not st.session_state.awaiting_confirm:
						for ind_response in ind_scores:
							ref.push(ind_response)
						show_review_prompt()

	else:
		st.error(f"Access denied for {sign_in_id or 'unknown user'}.")
		st.button("Log out", on_click=st.logout)
else:
	login_screen()



