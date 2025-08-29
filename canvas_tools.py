# Import the Canvas class
from canvasapi import Canvas
import tomllib 
from collections import defaultdict

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

		group_categories = self.course.get_group_categories()
		if group_categories:
			self.groups = group_categories[0].get_groups()
		else:
			self.groups = []
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
				self.student_data[member.name][1]= group.name


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
				print(f'{student_email}@umsystem.edu')
				print(f'{student_email}@mst.edu')
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


if __name__ == "__main__":
	mycanvas = CanvasTool()
	mycanvas.find_student_data()
	#mycanvas.print_student_emails()
	mycanvas.print_survey_config()

	#print(mycanvas.student_data)
	# print('uploading assignment')
	
	# grades = {
	# 	61507:(20,'nice job'),
	# 	62486:(30,'great work'),
	# }
	# mycanvas.upload_bulk_grades(3246434,grades)
