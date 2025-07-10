import streamlit as st

@st.dialog("Feedback submitted!")
def show_review_prompt():
	st.success("Your feedback has been recorded.")
	review_more = st.radio("Would you like to review another group?", ["No", "Yes"], key="review_more_dialog")

	if st.button("Continue"):
		if review_more == "Yes":
			for key in list(st.session_state.keys()):
				del st.session_state[key]
			st.rerun()
		else:
			st.markdown("Thank you for your feedback! 🎉")

# Set your password here
CORRECT_PASSWORD = "ME4842"

# Password input field
if "authenticated" not in st.session_state:
	st.session_state.authenticated = False

if not st.session_state.authenticated:
	password = st.text_input("Enter password to access the survey", type="password")
	if password == CORRECT_PASSWORD:
		st.session_state.authenticated = True
		st.rerun()
	elif password:
		st.error("Incorrect password")
else:
	st.success("Access granted!")



	st.title("ME4842 Proposal Presentation Feedback")
	st.header("Student Identification")

	# Student dictionary, orgaizned by section and group. GOAL: CREATE VIA CANVAS
	students_by_section_group = {
		"303": {
			"Group A": ["Alice Johnson", "Ben Smith", "Carla Diaz", "Daniel Wong"],
			"Group B": ["Eva Thompson", "Frank Li", "Grace Patel", "Henry Brooks"]
		},
		"304": {
			"Group A": ["Iris Kim", "Jake Turner", "Katie Lee", "Leo White"],
			"Group B": ["Maya Green", "Nathan Hall", "Olivia Jones", "Paul Singh"]
		},
		"305": {
			"Group A": ["Quinn Wright", "Riley Chen", "Sophia Adams", "Tyler Cook"],
			"Group B": ["Uma Patel", "Victor Lin", "Wendy Zhang", "Xavier Lee"]
		}
	}

	students_by_section = {
		section: [student for group in groups.values() for student in group]
		for section, groups in students_by_section_group.items()
	}

	#identify student
	section = st.selectbox("Select your section", options=["Select your section"] + list(students_by_section.keys()))
	if section != 'Select your section':
		student_name = st.selectbox("Select your name", options=["Select your name"] + list(students_by_section[section]))

	#Create questions for review, first select group to review
	st.header("Presentation Review")
	group = None
	if section != 'Select your section':
		group = st.selectbox("Select the group that is presenting", options=["Select your group"]+list(students_by_section_group[section].keys()))

	#create grid for students to track presentation order
	# Only proceed with questions if student group,section, and name have been selected, make sure default is not selected
	if section != "Select your section" and student_name != "Select your name" and group != "Select your group":
		st.markdown("Use this to visually track who is presenting in which order.")

		# Use actual students from selected section and group
		students = students_by_section_group[section][group]
		orders = [1, 2, 3, 4]

		# Initialize selection state for each student row
		for student in students:
			if f"selected_{student}" not in st.session_state:
				st.session_state[f"selected_{student}"] = None  # No selection yet

		# Draw header row
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
					st.session_state[selected_key] = order  # Set selected column
		
		individual_responses = ['Substandard',"Poor","Acceptable","Good","Excellent"]
		#create questions for each student within group
		for student in students:
			st.subheader(f"**Score {student}:**")
			dress_code = st.radio(f"**Dress Code**", individual_responses, key=f"dress_{student}")
			audience_engagement = st.radio(f"**Audience Engagement**", individual_responses, key=f"audience_engagement_{student}")
			body_language = st.radio(f"**Body Language**", individual_responses, key=f"body_language_{student}")
			enthusiasm = st.radio(f"**Enthusiasm**", individual_responses, key=f"enthusiasm_{student}")
			overall = st.radio(f"**Speaking**", individual_responses, key=f"speaking_{student}")
			comments = st.text_area(f"**Individual feedback for {student} (optional):**", key=f"ind_feedback_{student}")

		st.subheader(f"**Score {group}:**")
		group_comments = st.text_area(f"**Provide written overall feedback and presentation comments for {group} here (optional):**", key=f"group_feedback_{group}")
		group_technical = st.number_input(f"**Overall technical content.** Did {group} provide enough information for the audience to understand the topic? (0-10)",key=f"group_technical_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
		group_efficacy = st.number_input(f"**Overall efficacy of experimental plan.**  did {group} convince you that they will complete the experiment and acheive good results? (0-10)", key=f"group_efficacy_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
		group_completeness = st.number_input(f"**Overall completeness of proposal.** Did {group} leave out any important information? Did they propose the details of their experimental setup (i.e. specific instrumentation)?",key=f"group_completeness_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
		group_presentation_quality = st.number_input(f"**Overall presentation quality.** Did {group} effecitvley communicate their ideas? Did they speak clearly and use well made slides with good visual aids?",key=f"group_presentation_quality_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")
		group_answer_questions = st.number_input(f"**Overall ability to answer questions.** Did {group} work well together to answer the audience and reviewer questions?",key=f"group_answer_questions_{group}",min_value=0.0,max_value=10.0,step=0.1, format="%.1f")


		
		if st.button("Submit Feedback"):
			show_review_prompt()
