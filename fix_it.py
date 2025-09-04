import gspread
import toml
import json
import pandas as pd

#GRADER FOR ME4842 SURVEYS, THIS USES A STANDARD RESPONSE AND GRADEBOOK FOR ALL ASSIGNMENTS
class Grader:
	# Positions of points, rects, displacements
	def __init__(self):
		#student response book shape is {name: [assignment_id,responses]}
		self.student_responsebook = {}

		#student gradebook shape is {name: [weight, score, written_feedback]}
		self.student_gradebook = {}


	#######BOOK KEEPING FUNCTIONS########
	def organize_responses(self,):

		#Load the secrets from .streamlit/secrets.toml
		secrets = toml.load(".streamlit/secrets.toml")
		creds_dict = secrets['connections']['gsheets']

		# Fix escaped newlines in private key
		creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

		#authenticate with gspread using dict credentials
		gc = gspread.service_account_from_dict(creds_dict)
		spreadsheet = gc.open_by_url(creds_dict['spreadsheet'])
		
		# Loop through each sheet (except the first)
		for sheet in spreadsheet.worksheets()[1:]:
			responses = sheet.get_all_values()  # list of lists

			for response in responses[1:]: 
				data = response[1].split('$*')
				assignment_id = response[0]
				student_name = data[0]
				
				if student_name not in self.student_responsebook.keys():
					self.student_responsebook[student_name] = [[assignment_id,data]]
				else:
					self.student_responsebook[student_name].append([assignment_id,data])

	def go_fix_it(self,):
		groups = 1
		for student_name, responses in self.student_responsebook.items():
			print(student_name)
			if student_name == 'test':
				for assignment_id, data in responses:
					if assignment_id == 'Group_Lab_Selection':
						print('found the test')
	

	def create_groups(self,):
		groups = 1
		for student_name, responses in self.student_responsebook.items():
			for assignment_id, data in responses:
				if assignment_id == 'Group_Lab_Selection':
					pass



if __name__ == "__main__":
	grad = Grader()
	grad.organize_responses()
	grad.go_fix_it()

	# for grade in proposal_grades:
	# 	print(grade[2])
	#for student in grad.student_gradebook.keys():
		# print(student,grad.student_gradebook[student])
		# print('\n')