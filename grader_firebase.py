import gspread
import toml
import json
import pandas as pd
from pprint import pprint
from collections import Counter
import yaml
import stutts_picker as picker
import os
import shutil
import firebase_admin
from firebase_admin import credentials, db
import streamlit as st
import numpy as np

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
		if not firebase_admin._apps:
			#database authentication
			cred = dict(st.secrets["firebase_creds"])
			cred = credentials.Certificate(cred)
			firebase_admin.initialize_app(cred, {"databaseURL": "https://fs2025-me4842-default-rtdb.firebaseio.com/"})

	def grade_midterm_peer_evaluation(self,):
		ref = db.reference('Midterm_Peer_Evaluations')
		responses = ref.get()

		for user, data in responses.items():
			for key,response in data.items(): 
				reviewee = response['student_being_reviewed']
				if reviewee in self.student_responsebook.keys():
					self.student_responsebook[reviewee].append(response)
				else:
					self.student_responsebook[reviewee] = [response]
		
		self.midterm_peer_eval_gradebook = {}

		for student, responses in self.student_responsebook.items():
			ind_scores = {
				"labs": {"pts": 0, "total": 0},
				"meetings_score": {"pts": 0, "total": 0},
				"memos_score": {"pts": 0, "total": 0},
				"final_project_score": {"pts": 0, "total": 0},
				"comments": []
			}

			for response in responses:
				for question, score_data in ind_scores.items():
					if question == "comments":
						if response.get("comments"):
							score_data.append(response["comments"])
					else:
						score = response.get(question)
						if score is not None:
							ind_scores[question]["pts"] += float(score)
							ind_scores[question]["total"] += 5

			
			
			individual_score_normalized = sum(v["pts"] for v in ind_scores.values() if isinstance(v, dict)) / sum(v["total"] for v in ind_scores.values() if isinstance(v, dict))
			
			overall_score = (individual_score_normalized*10)


			text_feedback = f"""
			---------------------------------------------------
			{student}
			---------------------------------------------------
			Standard Lab participation: {(ind_scores["labs"]["pts"] / ind_scores["labs"]["total"])*10:.2f} / 10
			Contribution to group memos: {(ind_scores["memos_score"]["pts"] / ind_scores["memos_score"]["total"])*10:.2f} / 10
			Participation in group discussions / meetings: {(ind_scores["meetings_score"]["pts"] / ind_scores["meetings_score"]["total"])*10:.2f} / 10
			Work on final experiment: {(ind_scores["final_project_score"]["pts"] / ind_scores["final_project_score"]["total"])*10:.2f} / 10
			
			---------------------------------------------------
			Peer Evaluation Grade: {overall_score:.2f}/10 ----> {individual_score_normalized*100:.2f}%
			---------------------------------------------------
			Comments: {"\n-" + "\n-".join(ind_scores["comments"])} 


			"""

			self.midterm_peer_eval_gradebook[student] = [overall_score,text_feedback]
		return self.midterm_peer_eval_gradebook


	def grade_prop(self,database):
		#write response to Proposal database
		ref = db.reference(database)
		responses = ref.get()

		for key,response in responses.items(): 
			reviewee = response['student_being_reviewed']
			if isinstance(reviewee,list):
				for student in reviewee:
					if student in self.student_responsebook.keys():
						self.student_responsebook[student].append(response)
					else:
						self.student_responsebook[student] = [response]
			else:
				if reviewee in self.student_responsebook.keys():
					self.student_responsebook[reviewee].append(response)
				else:
					self.student_responsebook[reviewee] = [response]

		rating_map = {"Substandard": 2,"Poor": 2.75,"Acceptable": 3.5,"Good": 4.25,"Excellent": 5}

		#structured [[student name, grade, comments]]
		self.proposal_gradebook = {}

		for student,responses in self.student_responsebook.items():

			ind_scores = {
				"dress_code_score": {"pts": 0, "total": 0},
				"audience_engagement_score": {"pts": 0, "total": 0},
				"body_language_score": {"pts": 0, "total": 0},
				"enthusiasm_score": {"pts": 0, "total": 0},
				"overall_score": {"pts": 0, "total": 0},
				"written_feedback": []
			}
			group_scores = {
				"technical_content_score": {"pts": 0, "total": 0},
				"experimental_efficacy_score": {"pts": 0, "total": 0},
				"completeness_score": {"pts": 0, "total": 0},
				"presentation_quality_score": {"pts": 0, "total": 0},
				"answering_questions_score": {"pts": 0, "total": 0},
				"written_feedback": []
			}
			
			for response in responses:
				response_type = response['response_type']
				weight = response['scoring_weight']
				if response_type == 'Individual':
					for question, score_data in ind_scores.items():
						if question == "written_feedback":
							if response.get("written_feedback"):
								score_data.append(response["written_feedback"])
						else:
							label = response.get(question)
							if label is not None:
								numeric_score = rating_map[label]
								ind_scores[question]["pts"] += float(numeric_score) * weight
								ind_scores[question]["total"] += weight * 5
								if numeric_score == 1:
									print('found bad score')

				elif response_type == 'Group':
					group_name = response['group_being_scored']
					for question, score_data in group_scores.items():
						if question == "written_feedback":
							if response.get("written_feedback"):
								score_data.append(response["written_feedback"])
						else:
							score = response.get(question)
							if score is not None:
								if int(score) != 0:
									group_scores[question]["pts"] += float(score) * weight
									group_scores[question]["total"] += weight * 10

		
			individual_score_normalized = sum(v["pts"] for v in ind_scores.values() if isinstance(v, dict)) / sum(v["total"] for v in ind_scores.values() if isinstance(v, dict))
			group_score_normalized = sum(v["pts"] for v in group_scores.values() if isinstance(v, dict)) / sum(v["total"] for v in group_scores.values() if isinstance(v, dict))
			overall_score = (individual_score_normalized*25) + (group_score_normalized *10)


			text_feedback = f"""
			---------------------------------------------------
			Individual Scores: {student}
			---------------------------------------------------
			Dress Code: {(ind_scores["dress_code_score"]["pts"] / ind_scores["dress_code_score"]["total"] * 100):.2f}%
			Audience Engagement: {(ind_scores["audience_engagement_score"]["pts"] / ind_scores["audience_engagement_score"]["total"] * 100):.2f}%
			Body Language: {(ind_scores["body_language_score"]["pts"] / ind_scores["body_language_score"]["total"] * 100):.2f}%
			Enthusiasm: {(ind_scores["enthusiasm_score"]["pts"] / ind_scores["enthusiasm_score"]["total"] * 100):.2f}%
			Speaking: {(ind_scores["overall_score"]["pts"] / ind_scores["overall_score"]["total"] * 100):.2f}%
			
			Individual Score: {individual_score_normalized*100:.2f}%
			Individual Points: {individual_score_normalized*25:.2f} / 25

			Inidvidual Feedback Recieved: {"\n-" + "\n-".join(ind_scores["written_feedback"])} 
			---------------------------------------------------
			Group Scores: {group_name}
			---------------------------------------------------
			Technical: {(group_scores["technical_content_score"]["pts"] / group_scores["technical_content_score"]["total"] * 100):.2f}%
			Efficacy: {(group_scores["experimental_efficacy_score"]["pts"] / group_scores["experimental_efficacy_score"]["total"] * 100):.2f}%
			Completeness: {(group_scores["completeness_score"]["pts"] / group_scores["completeness_score"]["total"] * 100):.2f}%
			Presentation Quality: {(group_scores["presentation_quality_score"]["pts"] / group_scores["presentation_quality_score"]["total"] * 100):.2f}%
			Ability to Answer Questions: {(group_scores["answering_questions_score"]["pts"] / group_scores["answering_questions_score"]["total"] * 100):.2f}%
			
			Group Score: {group_score_normalized*100:.2f}%
			Group Points: {group_score_normalized*10:.2f} / 10
			
			Group Feedback Recieved: {"\n-" +"\n-".join(group_scores["written_feedback"])}
			---------------------------------------------------
			Final Assignment Grade
			---------------------------------------------------
			Group Score + Individual Score = Overall Score
			
			{individual_score_normalized*25:.2f} + {group_score_normalized*10:.2f}  = {overall_score:.2f}/35 ----> {overall_score*100/35:.2f}%\n

			"""

			self.proposal_gradebook[student] = [overall_score,text_feedback]
		return self.proposal_gradebook


	def create_groups(self,):
		group_letters = ['A','B','C','D','E']

		#formatted as {section:Group A, Group B...}
		student_groups = {}
		grouped_students = []

		for student_name, responses in self.student_responsebook.items():

			for assignment_id, data in responses:
				if assignment_id == 'Group_Lab_Selection':
					members, labs, section = data
					members = json.loads(members.replace("'",'"'))
					labs = json.loads(labs.replace("'",'"'))
					labs = ','.join(labs)

					if section not in student_groups.keys():
						student_groups[section] = {}
						student_groups[section][section+group_letters[0]] = {}
						student_groups[section][section+group_letters[0]]['Group Members'] = members
						student_groups[section][section+group_letters[0]]['Labs'] = labs
						grouped_students=grouped_students+members
					else:
						group_letter_idx = len(student_groups[section].keys())
						student_groups[section][section+group_letters[group_letter_idx]] = {}
						student_groups[section][section+group_letters[group_letter_idx]]['Group Members'] = members
						student_groups[section][section+group_letters[group_letter_idx]]['Labs'] = labs
						grouped_students=grouped_students+members


		student_counts = Counter()

		for section in student_groups.keys():
			for group in student_groups[section].keys():
				print(f'{group}: {student_groups[section][group]}')
				students = student_groups[section][group]['Group Members']
				student_counts.update(students)
		print(student_counts)
		secrets = toml.load(".streamlit/secrets.toml")
		students = secrets['class_list']['students']
	
		# (Section, Name, Group)

		students: list[tuple[str, str]] = [(info.split(',')[0], info.split(',')[-1]) for info in students]
		not_in_groups = []
		in_multiple_groups = []

		# Find students not assigned.
		for student in students:
			if student[1] not in student_counts.keys():
				print(student[1] + " is not in a group.")

				not_in_groups.append(student)
		
		# Find students in multiple groups.
		for student in student_counts:
			if student_counts[student] > 1:
				print(student + " is assigned to multiple groups.")

				# Search pre-existing list of students for name.
				student = next((s for s in students if s[1] == student), None)
				assert student is not None

				in_multiple_groups.append(student)
		
		if os.path.exists('groups.yml'):
			user_data = input('A groups.yml file already exisits. Do you want to overwrite it? (Y/N)\n')
			if user_data == "N" or 'n':
				return
			
		self.export_groups(student_groups, not_in_groups, in_multiple_groups)


	def assign_labs(self,):
		# Run picker

		pref_responses = {}

		shutil.rmtree("assignments", ignore_errors=True)
		os.mkdir("assignments")

		with open("groups.yml", "r") as f:
			data = yaml.safe_load(f)

		sections_data_yaml = {}

		for group in data['Groups']:
			group_name = list(group.keys())[0]
			section = group_name[0:3]
			if section in sections_data_yaml.keys():
				sections_data_yaml[section][group_name] = group[group_name]['Labs']
			else:
				sections_data_yaml[section] = {}
				sections_data_yaml[section][group_name] = group[group_name]['Labs']

		
		for section_name, data in sections_data_yaml.items():
			group_data = []
			for group_name, labs in data.items():
				labs = labs.split(',')
				group_data.append({
					"Group": group_name,
					"Electives": labs
				})

			groups, costs, ranks = picker.process_input_and_build_costs(group_data, ['Acoustics', 'Pump', 'Tuned Mass Damper', 'Dynamic Balancing', 'Piezoelectric'], unlisted_penalty=5, seed=1)

			# if len(groups) > 5:
			#     raise SystemExit(f"Infeasible: {len(groups)} groups but only 5 one-station electives per week. Split the section or add capacity.")
			result, status = picker.solve_ilp(groups, costs, T=2)
			if status != "ok":
				result, status = picker.solve_greedy(groups, costs, T=2)

			picker.write_output(f"assignments/{section_name}.xlsx", result, groups, costs, ranks, None, 5, T=2)
			print(json.dumps({"status": status, "total_cost": result["total_cost"], "groups": len(groups)}))


	def export_groups(self, student_groups: dict[str, dict[str, list[str]]], students_not_in_groups: list[tuple[str, str]], students_in_multiple_groups: list[str]):
		with open("groups.yml", "w") as f:


			groups = []
			for section in sorted(student_groups.keys()):
				for group in student_groups[section].keys():
					groups.append({group: student_groups[section][group]})
			
			# Sort by section.
			groups = sorted(groups, key=lambda k: list(k.keys())[0][:-1])
			header = {
				"Students in Multiple Groups": [{student[0]: student[1]} for student in students_in_multiple_groups],
				"Students not in Group": [{student[0]: student[1]} for student in students_not_in_groups]
			}

			data = {
				"Groups": groups
			}
			f.write(yaml.dump({"Information":"Please resolve all conflicts before uploading to Canvas. Do not delete conflict notes."}))
			f.write(yaml.dump(header))
			f.write(yaml.dump(data))
		

	
if __name__ == "__main__":
	grad = Grader()
	#grad.organize_responses()
	database = 'Midterm_Peer_Evaluations'
	grad.organize_responses()
	grad.grade_midterm_peer_evaluation()
	# for student,values in grad.proposal_gradebook.items():
	# 	print(values[1])

	# for grade in proposal_grades:
	# 	print(grade[2])
	grades = []
	for student in grad.midterm_peer_eval_gradebook.keys():
		
		print(grad.midterm_peer_eval_gradebook[student][1])
		print('\n')
	# with open("proposal_grades.txt", "w") as f:
	# 	for student in grad.proposal_gradebook.keys():
	# 		f.write(str(grad.proposal_gradebook[student][1]) + "\n\n")
