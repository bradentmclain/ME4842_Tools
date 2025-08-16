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


	######GRADING FUNCTIONS FOR EACH RESPONSE, ADD THEM TO GRADE BOOK#########

	#grading function for individual response to project proposal presentation
	def grade_proposal_individual(self,data):
		#this is out of a total of 25 points, score normailzed to 1
		weight = 1


		name = data[1]
		print(f'name is {name}')

		if name not in self.student_gradebook.keys():
			self.student_gradebook[name] = [[weight,multiple_choice_responses,written_responses]]
		else:
			self.student_gradebook[name].append([weight,multiple_choice_responses,written_responses])
		


	#grading function for group response to project proposal presentation
	def grade_proposal_group(self,data):
		#this is out of a total of 50, normalized to 1
		weight = 1
		group_name = data[1]
		scores = data[3:7]
		total_score = sum(float(r) for r in scores)/50
		written_responses = data[2]	
		if group_name not in self.student_gradebook.keys():
			self.student_gradebook[group_name] = [[weight,total_score,written_responses]]
		else:
			self.student_gradebook[group_name].append([weight,total_score,written_responses])


	#######BOOK KEEPING FUNCTIONS########
	def organize_responses(self,):

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
				
				if student_name not in self.student_responsebook.keys():
					self.student_responsebook[student_name] = [[assignment_id,data]]
				else:
					self.student_responsebook[student_name].append([assignment_id,data])

		for student_name, responses in self.student_responsebook.items():
			for assignment_id, data in responses:
				name = data[1]
				if ',' in name:
					names = name.split(',')
					
					for name in names:
						print(f'found these from a group{name}')
						if name not in self.student_gradebook.keys():
							self.student_gradebook[name] = [[assignment_id, data]]
						else:
							self.student_gradebook[name].append([assignment_id, data])
				else:
					print(f'found these not in a group{name}')
					if name not in self.student_gradebook.keys():
						self.student_gradebook[name] = [[assignment_id, data]]
					else:
						self.student_gradebook[name].append([assignment_id, data])

	def grade_proposal(self,):
		individual_response_options = ['Substandard', 'Poor', 'Acceptable', 'Good', 'Excellent']
		response_scores = {resp: i + 1 for i, resp in enumerate(individual_response_options)}

		for student in self.student_gradebook.keys():
			ind_scores = {}
			group_scores = {}
			
			for assignment_id, data in self.student_gradebook[student]:
				if assignment_id == 'Proposal_Individual':
					#data = reviewer name, reviewee name, group, dress score, engagement score, body language score, enthusiasm score, speaking score, comments
					weight = 1

					pass
				elif assignment_id == 'Proposal_Group':
					pass
		   
		multiple_choice_responses = data[3:7]
		written_responses = data[8]
		total_score = sum(response_scores.get(r, 0) for r in multiple_choice_responses)/25

		pass


if __name__ == "__main__":
	grad = Grader()
	grad.organize_responses()
	print(grad.student_gradebook)



	# # Only grade 'Proposal'-related functions
	# grad.grade_assignments(['Proposal'])
	# # for student in self.student_responsebook.keys():
	# # 	print(f'student is {student}')
	# # 	print(f'responses are {self.student_responsebook[student]}')
	# print(grad.student_gradebook)





