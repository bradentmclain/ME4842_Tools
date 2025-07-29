# Import the Canvas class
from canvasapi import Canvas
import tomllib 
from collections import defaultdict

class CanvasTool:
	# Positions of points, rects, displacements
	def __init__(self):
		with open("./.canvas/canvas_secrets.toml", "rb") as f:
			config = tomllib.load(f)
		
		API_KEY = config['canvas']['API_KEY']
		API_URL = config['canvas']['API_URL']
		COURSE_ID = config['canvas']['COURSE_ID']
		
		canvas = Canvas(API_URL, API_KEY)
		course = canvas.get_course(COURSE_ID)

		group_categories = course.get_group_categories()
		self.groups = group_categories[0].get_groups()
		self.teachers = course.get_users(enrollment_type=['teacher'])

		self.sections = course.get_sections()
	
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
				self.student_data.update({student_name:[section_name,'None']})
		#add students to groups
		for group in self.groups:
			members = group.get_users()
			for member in members:
				self.student_data[member.name][1]= group.name


	def print_survey_config(self):
		#use this function to create the secrets file for survey configuration
		print(f'Paste this into your secrets.toml file:\n')
		print('students = [')
		for key in self.student_data:
			section = self.student_data[key][0].split('-')[-1]
			group = self.student_data[key][1].replace(" ","")
			print(f'"{section},{group},{key}",')
		print(']')

	def print_student_emails(self):
		#use this function to print student emails
		pass



if __name__ == "__main__":
	mycanvas = CanvasTool()
	mycanvas.find_student_data()
	mycanvas.print_survey_config()
	for teach in mycanvas.teachers:
		print(teach.name)
