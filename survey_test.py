import streamlit as st
import time
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from collections import defaultdict


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

#submission dialog popup
@st.dialog("Feedback submitted!")
def show_review_prompt():
	st.success(f"Thanks for your feedback {st.session_state['active_user'].split(" ")[0]}!")
	st.write("Would you like to review another group? If so, please select ''Review Again' below. Otherwise, you may now close the survey.")
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


####Begin UI Here
st.title("ME4842 Proposal Presentation Feedback")
st.header("Student Identification")


ind_scores = []
group_scores = []

#user identification, must be sequential
section_dropdown = st.selectbox("Select your section", options=["Click to Select"] + list(students_by_section.keys()),key='active_section')
if st.session_state['active_section'] != 'Click to Select':
	student_name_dropdown = st.selectbox("Select your name", options=["Click to Select"] + list(students_by_section[st.session_state['active_section']]),key='active_user')

#Select group to review
st.header("Presentation Review")
if st.session_state['active_section'] != 'Click to Select':
	group = st.selectbox("Select the group that is presenting", options=["Click to Select"]+list(students_by_section_group[st.session_state['active_section']].keys()),key='active_group',index=0)
	st.write(st.session_state['active_group'])


# Only proceed with questions if student group,section, and name have been selected, make sure default is not selected
#ask questions about each student in group, create visual grid as well
if st.session_state['active_section'] != "Click to Select" and st.session_state['active_user'] != "Click to Select" and st.session_state['active_group'] != "Click to Select":
	st.markdown("Use this to visually track who is presenting in which order.")

	students = students_by_section_group[st.session_state['active_section']][group]
	orders = [1, 2, 3, 4]
	

	# Initialize selection state for each student row
	for student in students:
		if f"selected_{student}" not in st.session_state:
			st.session_state[f"selected_{student}"] = None  # No selection yet

	cols = st.columns(len(orders) + 1)
	cols[0].markdown(" ")  # Empty top-left
	for i, order in enumerate(orders):
		cols[i + 1].markdown(f"**{order}**")

	# Grid body
	for student in students:
		cols = st.columns(len(orders) + 1)
		cols[0].markdown(f"**{student}**")
		for i, order in enumerate(orders):
			key = f"{student}-{order}"
			selected_key = f"selected_{student}"

			# Determine symbol to show
			is_selected = st.session_state[selected_key] == order
			label = "🔘" if is_selected else "◯"

			# Button press updates selected order for that row
			if cols[i + 1].button(label, key=key):
				st.session_state[selected_key] = order 
	
	#individual survey questions
	individual_responses = ['Substandard',"Poor","Acceptable","Good","Excellent"]
	for student in students:
		st.subheader(f"**Score {student}:**")
		dress_code = st.radio(f"**Dress Code**", individual_responses, key=f"ind_dress_{student}",index=0)
		audience_engagement = st.radio(f"**Audience Engagement**", individual_responses, key=f"ind_audience_engagement_{student}",index=0)
		body_language = st.radio(f"**Body Language**", individual_responses, key=f"ind_body_language_{student}",index=0)
		enthusiasm = st.radio(f"**Enthusiasm**", individual_responses, key=f"ind_enthusiasm_{student}",index=0)
		overall = st.radio(f"**Speaking**", individual_responses, key=f"ind_speaking_{student}",index=0)
		comments = st.text_area(f"**Individual feedback for {student} (optional):**", key=f"ind_feedback_{student}")
		
		#store responses in string to save as df
		ind_feedback_string = "$*".join([
			st.session_state.active_user,
			student,
			st.session_state.active_group,
			dress_code,
			audience_engagement,
			body_language,
			enthusiasm,
			overall,
			comments
			])
		
		ind_scores.append({
			"Survey_ID": "Proposal_Individual",
			"Feedback": ind_feedback_string
		})

	#group survey question
	st.subheader(f"**Score {group}:**")
	group_comments = st.text_area(f"**Provide written overall feedback and presentation comments for {group} here (optional):**", key=f"group_feedback_{group}")
	group_technical = st.number_input(f"**Overall technical content.** Did {group} provide enough information for the audience to understand the topic? (0-10)",key=f"group_technical_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
	group_efficacy = st.number_input(f"**Overall efficacy of experimental plan.**  did {group} convince you that they will complete the experiment and achieve good results? (0-10)", key=f"group_efficacy_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
	group_completeness = st.number_input(f"**Overall completeness of proposal.** Did {group} leave out any important information? Did they propose the details of their experimental setup (i.e. specific instrumentation)?",key=f"group_completeness_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
	group_presentation_quality = st.number_input(f"**Overall presentation quality.** Did {group} effectively communicate their ideas? Did they speak clearly and use well made slides with good visual aids?",key=f"group_presentation_quality_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
	group_answer_questions = st.number_input(f"**Overall ability to answer questions.** Did {group} work well together to answer the audience and reviewer questions?",key=f"group_answer_questions_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")

	#store responses in string to save as df
	group_feedback_string = "$*".join([
		st.session_state.active_user,
		st.session_state.active_group,
		str(group_comments),
		str(group_technical),
		str(group_efficacy),
		str(group_completeness),
		str(group_presentation_quality),
		str(group_answer_questions)
		])
	
	group_scores = {
		"Survey_ID": "Proposal_Group",  # or your preferred ID
		"Feedback": group_feedback_string
	}
	group_df = pd.DataFrame([group_scores])

	#on data submission
	if st.button("Submit Feedback"):
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
				group_df = pd.DataFrame([group_scores])
				conn.update(worksheet=st.session_state.active_user,data=pd.concat([prev_data,ind_df,group_df]))
			else:
				ind_df = pd.DataFrame(ind_scores)
				group_df = pd.DataFrame([group_scores])
				conn.create(worksheet=st.session_state.active_user, data=pd.concat([ind_df,group_df]))
		#after data has been uploaded, ask if user wants to review another group
		show_review_prompt()
