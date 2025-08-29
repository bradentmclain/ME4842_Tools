import streamlit as st
import time
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from collections import defaultdict
import random


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

if "active_user" not in st.session_state:
	st.session_state.active_user = "Click to Select"

#import student data from toml file
nested = defaultdict(lambda: defaultdict(list))

for entry in st.secrets["class_list"]["students"]:
	sec, grp, nm = entry.split(",", 2)
	sec, grp, nm = sec.strip(), grp.strip(), nm.strip()
	nested[sec][grp].append(nm)

students_by_section_group = {s: dict(groups) for s, groups in nested.items()}

students_by_section = {
	section: [student for group in groups.values() for student in group]
	for section, groups in students_by_section_group.items()
}
all_students = [student for students in students_by_section.values() for student in students]

#submission dialog popup
@st.dialog("Feedback submitted!")
def show_complete_prompt():
	st.success(f"Thanks for your filling out the survey! You can now close the webpage.")


available_labs = ['Dynamic Balancing', "Tuned Mass Damper", 'Pump','Acoustics',"Piezoelectric"]

####Begin UI Here
st.title("ME4842 Group Creation and Lab Selection")



ind_scores = []
group_scores = []
weight = random.choice([1,2])

#user identification, must be sequential
section_dropdown = st.selectbox("Select your section:", options=["Click to Select"] + list(students_by_section.keys()),key='active_section')

roster = students_by_section.get(st.session_state['active_section'], [])


active_user = st.selectbox("Please Select Your Name", options=['Click to Select']+roster,key=f'active_user')

selected_names = []
if st.session_state['active_section'] != 'Click to Select' and st.session_state['active_user'] != 'Click to Select':
	st.header("Group Identification")
	number_group_members = st.number_input(f"How many students will be in your group?",min_value=3,max_value=5,step=1,key='number_group_members')

	for i in range(st.session_state['number_group_members']):
		if i == 0:
			index = roster.index(st.session_state['active_user']) if st.session_state['active_user'] in roster else 0
			student_name_dropdown = st.selectbox("Add group member", options=['Click to Select']+roster,key=f'student_name_dropdown_{i}',index=index+1)
			selected_names.append(st.session_state[f'student_name_dropdown_{i}'])
		else:
			student_name_dropdown = st.selectbox("Add group member", options=['Click to Select']+roster+['Student is transferring from a different section'],key=f'student_name_dropdown_{i}')
			if st.session_state[f'student_name_dropdown_{i}'] == 'Student is transferring from a different section':
				student_name_dropdown = st.selectbox("Add transferring group member", options=['Click to Select']+all_students,key = f'student_outside_section_{i}')
				selected_names.append(st.session_state[f'student_outside_section_{i}'])
			else:
				selected_names.append(st.session_state[f'student_name_dropdown_{i}'])

#Select group to review

selected_labs =[]
if st.session_state['active_section'] != 'Click to Select' and st.session_state['active_user'] != 'Click to Select':
	st.header("Lab Selection")
	for lab in range(len(available_labs)):
		lab_dropdown = st.selectbox(f"Select lab preference {lab+1}", options=["Click to Select"]+available_labs,key=f'selected_labs_{lab}')
		selected_labs.append(st.session_state[f'selected_labs_{lab}'])
allow_submit = True
statement = ''

if "Click to Select" in selected_names:
	allow_submit = False
	statement = 'Please finish the survey before submitting!'
elif "Click to Select" in selected_labs:
	allow_submit = False
	statement = 'Please finish the survey before submitting!'
elif len(selected_names) != len(set(selected_names)):
	allow_submit = False
	statement = 'Please remove duplicate students before submitting!'
elif len(selected_labs) != len(set(selected_labs)):
	allow_submit = False
	statement = 'Please remove duplicate lab selections before submitting!'

if st.session_state['active_section'] != 'Click to Select' and st.session_state['active_user'] != 'Click to Select':
	if statement != '':
		st.write(statement)
	if st.button("Submit", disabled=not allow_submit):
		feedback_string = "$*".join([
		str(selected_names),
		str(selected_labs)
		])
	
		feedback = {
			"Survey_ID": "Group_Lab_Selection",  # or your preferred ID
			"Data": feedback_string
		}
		feedback_df = pd.DataFrame([feedback])
		
		# create new connection, create new worksheet for individual user
		conn = st.connection("gsheets", type=GSheetsConnection)
		with st.spinner("Uploading Data...", show_time=True):
			sh = conn._instance._open_spreadsheet()
			worksheets = sh.worksheets()
			available_sheets = []
			#gather all worksheets
			for worksheet in worksheets:
				available_sheets.append(worksheet.title)
			#if a worksheet exists, append to it. if not, make a new one
			if st.session_state.active_user in available_sheets:
				prev_data = conn.read(worksheet=st.session_state.active_user, ttl=0)
				ind_df = pd.DataFrame(ind_scores)

				conn.update(worksheet=st.session_state.active_user,data=pd.concat([prev_data,feedback_df]))
			else:
				ind_df = pd.DataFrame(ind_scores)
				conn.create(worksheet=st.session_state.active_user, data=pd.concat([ind_df,feedback_df]))
		#after data has been uploaded, ask if user wants to review another group
		show_complete_prompt()

