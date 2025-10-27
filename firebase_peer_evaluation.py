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
	st.subheader("Please log in.")
	st.button("Log in with Google", on_click=st.login)

def all_scores_filled(ind_scores):
	scored_filled = True
	for response_dict in ind_scores:
		for key in response_dict.keys():
			if response_dict[key] == None or response_dict[key] == '':
				scored_filled = False
	return scored_filled


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
	for email_id in student_dict.keys():
		if email_id == sign_in_id:
			is_allowed = True
	return is_allowed

students_by_section_group = {s: dict(groups) for s, groups in nested.items()}

students_by_section = {
	section: [student for group in groups.values() for student in group]
	for section, groups in students_by_section_group.items()
}

#submission dialog popup
@st.dialog("Feedback submitted!")
def show_review_prompt():
	# fixed quoting inside f-string below
	st.success(f"Thanks for your feedback {st.session_state['active_user'].split(' ')[0]}! Your responses have been recorded.")

def init_firebase():
	# Only initialize once
	if not firebase_admin._apps:
		#database authentication
		cred = dict(st.secrets["firebase_creds"])
		cred = credentials.Certificate(cred)
		firebase_admin.initialize_app(cred, {"databaseURL": "https://fs2025-me4842-default-rtdb.firebaseio.com/"})

init_firebase()
#write response to Proposal database
ref = db.reference("Midterm_Peer_Evaluations")

if st.user.is_logged_in:
	# Safely extract claims (st.user is dict-like)
	sign_in_dict = dict(st.user)
	sign_in_id = sign_in_dict.get("email").split('@')[0]
	sign_in_name = sign_in_dict.get("name", "User")

	if is_allowed(sign_in_id):
		
		st.success(f"You are successfully logged in, {sign_in_name}.")
		####Begin UI Here
		st.title("ME4842 Proposal Presentation Feedback")
		st.header("Student Identification")

		ind_scores = []

		#user identification, must be sequential
		# section_dropdown = st.selectbox("Select your section",options=["Click to Select"] + list(students_by_section.keys()),key='active_section')
		st.session_state['active_section'] = student_dict[sign_in_id]['section']
		st.session_state['active_group'] = student_dict[sign_in_id]['group']
		st.session_state['active_user'] = student_dict[sign_in_id]['name']

		ref = db.reference(f"Midterm_Peer_Evaluations/{st.session_state['active_user']}")
		
		st.markdown(f'#### Your Name: :green[{st.session_state["active_user"]}]')
		st.markdown(f'#### Your Group: :green[{st.session_state["active_group"]}]')
		st.write(f'If this is incorrect please contact Braden at btmywv@mst.edu')
		# ------- Name selection with "I am an instructor" flow + passphrase (persistent) -------
		# if st.session_state['active_section'] != 'Click to Select':
		# 	# include instructor sentinel option
		# 	name_options = ["Click to Select"] + list(students_by_section[st.session_state['active_section']])

		# 	user = st.selectbox("Select your name", options=name_options, key='active_user')

		#Select group to review
		st.header("Peer Evaluation")
		if st.session_state['active_section'] != 'Click to Select':
			group = st.selectbox("Select the group that is presenting",	options=["Click to Select"] + sorted(list(students_by_section_group[st.session_state['active_section']].keys())),key='active_group',index=0)

			if group != 'Click to Select':
				students = students_by_section_group[st.session_state['active_section']][group]
				for student in students:
					st.subheader(f"**Score {'Yourself' if student == st.session_state.active_user else student}:**")
					
					st.markdown(f"##### Evaluation of {'your' if student == st.session_state.active_user else student+"'s"} participation during the three standard lab experiments")
					labs = st.number_input(f"How much this person contributed to the three standard lab experiments on a scale from 0 to 5. 0 is no contribution, 5 is full expected individual contribution.", key=f"labs_{student}", min_value=0.0, max_value=5.0, step=0.1, format="%.1f", value=None)
					st.markdown(f"##### Evaluation of {'your' if student == st.session_state.active_user else student+"'s"} contribution to Memo 2 and Memo 3"); 
					memos = st.number_input(f"How much work this person contributed to the group memo assignments on a scale from 0 to 5. 0 is no contribution, 5 is full expected individual contribution.", key=f"memos_{student}", min_value=0.0, max_value=5.0, step=0.1, format="%.1f", value=None)
					st.markdown(f"##### Evaluation of {'your' if student == st.session_state.active_user else student+"'s"} participation during group discussions and meetings"); 
					meetings = st.number_input(f"How much this person contributed to the group discussions and meetings on a scale from 0 to 5. 0 is no contribution, 5 is full expected individual contribution.", key=f"meetings_{student}", min_value=0.0, max_value=5.0, step=0.1, format="%.1f", value=None)
					st.markdown(f"##### Evaluation of {'your' if student == st.session_state.active_user else student+"'s"} work on the Final Experiment materials and project"); 
					final_project = st.number_input(f"How much this person contributed on the Final Experiment Proposal Presentation, inital concept generation, and concept generation revision on a scale from 0 to 5. 0 is no contribution, 5 is full expected individual contribution.", key=f"final_{student}", min_value=0.0, max_value=5.0, step=0.1, format="%.1f", value=None)
					st.markdown(f"##### Written evaluation of {'your' if student == st.session_state.active_user else student+"'s"} work so far this semester."); 
					comments = st.text_area(f"Summarize the details of this persons work and contributions to the ME4842 group.", key=f"comments{student}")

					ind_feedback_dict = {
						"response_type":'Individual',
						"active_user": st.session_state.active_user,
						"student_being_reviewed": student,
						"labs": labs,
						"memos_score": memos,
						"meetings_score": meetings,
						"final_project_score": final_project,
						"comments": comments,
					}
					ind_scores.append(ind_feedback_dict)

				#group survey question

				is_complete = all_scores_filled(ind_scores)
				#on data submission
				if not is_complete:
					st.write('Please complete all required fields before submitting.')
				if st.button("Submit Feedback", disabled = not is_complete):
					if not st.session_state.awaiting_confirm:
						if ref.get():
							st.session_state.awaiting_confirm = True
						else:
							for ind_response in ind_scores:
								ref.push(ind_response)
							show_review_prompt()

				if st.session_state.awaiting_confirm:
					st.warning("It looks like you have already submitted feedback for this survey. Would you like to overwrite your previous submission? If not you may close the page.")
					if st.button('Confirm'):
						ref.delete()
						for ind_response in ind_scores:
							ref.push(ind_response)
						show_review_prompt()
						
	else:
		st.error(f"Access denied for {sign_in_id or 'unknown user'}.")
		st.button("Log out", on_click=st.logout)
else:
	login_screen()



