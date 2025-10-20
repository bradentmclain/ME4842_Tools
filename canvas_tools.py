# Import the Canvas class
from canvasapi import Canvas
import tomllib 
from collections import defaultdict
import yaml

class CanvasTool:
	# Positions of points, rects, displacements
	def __init__(self, COURSE_ID = None):
		with open("./.canvas/canvas_secrets.toml", "rb") as f:
			config = tomllib.load(f)
		
		API_KEY = config['canvas']['API_KEY']
		API_URL = config['canvas']['API_URL']

		if COURSE_ID == None:
			COURSE_ID = config['canvas']['COURSE_ID']
		
		canvas = Canvas(API_URL, API_KEY)
		self.course = canvas.get_course(COURSE_ID)

		self.group_categories = self.course.get_group_categories()
		for category in self.group_categories:
			if category.name == 'Project Groups':
				self.project_groups_category_id = category.id
				self.project_group_category = category

		self.groups = self.project_group_category.get_groups()
		self.teachers = self.course.get_users(enrollment_type=['teacher'])

		self.sections = self.course.get_sections()
	
	def find_student_data(self):
		#use this function to gather all relevent student data
		self.student_data = {}

		#go through each section
		for section in self.sections:
			section_name = section.name
			enrollments = section.get_enrollments(type=["StudentEnrollment"])
			#list each student in each section add them to main list
			for enrollment in enrollments:
				user = enrollment.user
				student_name = user['name']
				self.student_data.update({student_name:[user['id'],section_name,'None']})
		#add students to groups
		for group in self.groups:
			members = group.get_users()
			for member in members:
				self.student_data[member.name][2]= group.name


	def print_survey_config(self):
		#use this function to create the secrets file for survey configuration
		print(f'Paste this into your secrets.toml file:\n')
		print('students = [')
		for student in self.student_data:
			section = self.student_data[student][1].split('-')[-1]
			group = self.student_data[student][2].replace(" ","")
			print(f'"{section},{group},{student}",')
		print(']')

	def print_student_emails(self):
		#use this function to print student emails
		for section in self.sections:
			section_name = section.name
			enrollments = section.get_enrollments(type=["StudentEnrollment"])
			#list each student in each section add them to main list
			for enrollment in enrollments:
				user = enrollment.user
				student_email = user['login_id']
				print(f'{student_email}@umsystem.edu,')
		pass

	def upload_single_grade(self, assignment_id: int,student_id: int, score: float, comment: str = ""):
		#use this to submit one grade, pass an assignment id, a student id, assignment score and comment
		assignment = self.course.get_assignment(assignment_id)
		submission = assignment.get_submission(student_id)
		submission.edit(submission={"posted_grade": score},comment={"text_comment": comment})

		print(f"Uploaded grade {score} for user {student_id} with comment: {comment}")

	def upload_bulk_grades(self, assignment_id: int, grades: dict):
		#use this to submit a bunch of grades at once
		#grades dict in form {student_id:('posted_grade':'comments')}
		
		grade_data = {}
		for student_id, (score, comment) in grades.items():
			grade_data[str(student_id)] = {
				"posted_grade": score,
				"text_comment": comment
			}
		self.course.submissions_bulk_update(
			assignment_id=assignment_id,
			grade_data=grade_data
		)
		print(f"Uploaded {len(grades)} grades for assignment {assignment_id}")
	
	def upload_groups(self):
		#add more error checking
		error = False
		with open("groups.yml", "r") as f:
			data = yaml.safe_load(f)

		students = []
		for group in data['Groups']:
			group_name = list(group.keys())[0]
			print(group_name)
			for student in group[group_name]['Group Members']:
				students.append(student)

		
		for ungrouped in data['Students not in Group']:
			for section, ungrouped_student in ungrouped.items():
				if ungrouped_student not in students:
					print(f'{ungrouped_student} has not been added to a group. Please resolve in groups.yml')
					error = True
		
		for double_booked in data['Students in Multiple Groups']:
			for section, double_booked_student in double_booked.items():
				if students.count(double_booked_student) > 1:
					print(f'{double_booked_student} is in more than one group. Please resolve in groups.yml')
					error = True

		if error:
			return
		
		existing_canvas_group_names = []
		for g in self.groups:
			existing_canvas_group_names.append(g.name)

		#create necessary groups
		for groups in data['Groups']:
			group_name = list(group.keys())[0]
			if group_name not in existing_canvas_group_names:
				#self.project_group_category.create_group(name=group_name)
				print(f'gonna create {group_name.name}')

		#add students to respective groups
		for groups in data['Groups']:
			group_name = list(groups.keys())[0]
			for student in groups[group_name]['Group Members']:
				groups = list(self.project_group_category.get_groups())
				print(f'loading group {group_name}')
				canvas_group = next((g for g in groups if g.name == group_name), None)
				if canvas_group != None:
					uid = self.student_data[student][0]
					print(f'adding student {student} to group {canvas_group.name}')
					#canvas_group.create_membership(user=uid)

						

if __name__ == "__main__":
	mycanvas = CanvasTool()
	mycanvas.find_student_data()

	#mycanvas.upload_groups()
	#print(mycanvas.student_data)
	#mycanvas.print_student_emails()
	mycanvas.print_survey_config()

	#print(mycanvas.student_data)
	# print('uploading assignment')
	
	# grades = {
	# 	61507:(20,'nice job'),
	# 	62486:(30,'great work'),
	# }
	# mycanvas.upload_bulk_grades(3246434,grades)
