from grader import Grader
from canvas_tools import CanvasTool
import time

grad = Grader()
grad.organize_responses()

#proposal grades in form {student:[grade,text feedback]}
proposal_grades = grad.grade_proposal()

mycanvas = CanvasTool()
mycanvas.find_student_data()

#student data in form {student:[id,section,group]}
course_list = mycanvas.student_data

#grade submissions in form {student_id:(grade,comments)}
grades = {}

for student in proposal_grades.keys():
	if str(student) in course_list.keys():
		id,section,group = course_list[student]
		score,comment = proposal_grades[student]
		grades[id] = (score,comment)
	else:
		print(f'could not find {student} in course')

assignment_id = 3246434
start = time.time()

mycanvas.upload_bulk_grades(assignment_id,grades)

print(f'grade upload took {time.time()-start} seconds')