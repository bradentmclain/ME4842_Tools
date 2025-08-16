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
	print(f'grading group {group_name}')
	
	if group_name not in student_gradebook.keys():
		student_gradebook[group_name] = [[weight,total_score,written_responses]]
	else:
		student_gradebook[group_name].append([weight,total_score,written_responses])


#######BOOK KEEPING FUNCTIONS########
def create_response_book():
	# Load the Excel file
	xls = pd.ExcelFile("Database.xlsx")  # local file path

	# Loop through each sheet (except the first)
	for sheet_name in xls.sheet_names[1:]:
		df = xls.parse(sheet_name)
		responses = df.values.tolist() 

		for response in responses[1:]: 
			data = response[1].split('$*')
			assignment_id = response[0]
			student_name = data[0]
			
			if student_name not in student_responses.keys():
				student_responses[student_name] = [[assignment_id,data]]
			else:
				student_responses[student_name].append([assignment_id,data])


#GRADE SELECTED RESPONSES





if __name__ == "__main__":
	create_response_book()
	for student_name in student_responses.keys():
		for response in student_responses[student_name]:
			if response[0] == 'Prop_Ind':
				grade_prop_ind(response[1])
			elif response[0] == 'Prop_Group':
				grade_prop_group(response[1])
				print('grading a group assignment')
	print(student_gradebook)








