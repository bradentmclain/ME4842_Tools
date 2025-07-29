import gspread
import toml
import json
import pandas as pd

import pandas as pd
import time

#GRADER FOR ME4842 SURVEYS, THIS USES A STANDARD RESPONSE AND GRADEBOOK FOR ALL ASSIGNMENTS

#student response book shape is {name: [assignment_id,responses]}
student_responses = {}

#student gradebook shape is {name: [weight, score, written_feedback]}
student_gradebook = {}

######GRADING FUNCTIONS FOR EACH RESPONSE, ADD THEM TO GRADE BOOK#########

#grading function for individual response to project proposal presentation
def grade_prop_ind(data):
	#this is out of a total of 25 points, score normailzed to 1
	weight = 1

	individual_response_options = ['Substandard', 'Poor', 'Acceptable', 'Good', 'Excellent']
	response_scores = {resp: i + 1 for i, resp in enumerate(individual_response_options)}
	
	multiple_choice_responses = data[3:7]
	written_responses = data[8]
	total_score = sum(response_scores.get(r, 0) for r in multiple_choice_responses)/25

	name = data[1]

	if name not in student_gradebook.keys():
		student_gradebook[name] = [[weight,total_score,written_responses]]
	else:
		student_gradebook[name].append([weight,total_score,written_responses])

#grading function for group response to project proposal presentation
def grade_prop_group(data):
	#this is out of a total of 50, normalized to 1
	weight = 1
	group_name = data[1]
	scores = data[3:7]
	total_score = sum(float(r) for r in scores)/50
	written_responses = data[2]	
	if group_name not in student_gradebook.keys():
		student_gradebook[group_name] = [[weight,total_score,written_responses]]
	else:
		student_gradebook[group_name].append([weight,total_score,written_responses])


#######BOOK KEEPING FUNCTIONS########
def create_response_book():

	# --- Load the secrets from .streamlit/secrets.toml ---
	secrets = toml.load(".streamlit/secrets.toml")
	creds_dict = secrets['connections']['gsheets']


	# Fix escaped newlines in private key
	creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

	# --- Authenticate with gspread using dict credentials --- 
	
	gc = gspread.service_account_from_dict(creds_dict)

	# --- Open the sheet ---
	spreadsheet = gc.open_by_url(creds_dict['spreadsheet'])
	
	# Loop through each sheet (except the first)
	for sheet in spreadsheet.worksheets()[1:]:
		responses = sheet.get_all_values()  # list of lists

		for response in responses[1:]: 
			data = response[1].split('$*')
			assignment_id = response[0]
			student_name = data[0]
			
			if student_name not in student_responses.keys():
				student_responses[student_name] = [[assignment_id,data]]
			else:
				student_responses[student_name].append([assignment_id,data])


def grade_assignments(target_assignments=None):
	for student_name, responses in student_responses.items():
		for assignment_id, data in responses:
			grading_meta = GRADING_FUNCTIONS.get(assignment_id)

			if grading_meta is None:
				print(f"⚠️ No grading function for '{assignment_id}'")
				continue

			# Only grade if it's in the list of requested assignment groups
			if target_assignments is None or grading_meta['assignment'] in target_assignments:
				grading_meta['func'](data)


GRADING_FUNCTIONS = {
	'Prop_Ind':{'func': grade_prop_ind,'assignment': 'Proposal'},
	'Prop_Group':{'func': grade_prop_group,'assignment': 'Proposal'},
}

if __name__ == "__main__":
	create_response_book()

	# Only grade 'Proposal'-related functions
	grade_assignments(['Proposal'])
	print(student_gradebook)




