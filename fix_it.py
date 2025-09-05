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
	# .streamlit/secrets.toml

		self.students = [
		"301,None,Carter Allen",
		"301,None,Micah Asbill",
		"301,None,Cavitt Bruhn",
		"301,None,Anna Finley",
		"301,None,Clairese Kluba",
		"301,None,Benjamin Lampe",
		"301,None,Aidan Lesnik",
		"301,None,Griffin Mills",
		"301,None,Tyson Pilla",
		"301,None,Dominic Ponciroli",
		"301,None,Gunnar Rutherford",
		"301,None,Rebekah Settles",
		"301,None,Shiane Taylor",
		"301,None,Madison Vieth",
		"301,None,Henry Wilson",
		"302,None,Ryan Clapp",
		"302,None,Tucker Cudmore",
		"302,None,Joseph Day",
		"302,None,Alonzo Edmond",
		"302,None,David Frasca",
		"302,None,Ethan Haile",
		"302,None,Erik Hanson",
		"302,None,Paulvin Horton",
		"302,None,Nequan Johnson",
		"302,None,John Niebrugge",
		"302,None,Levi Opp",
		"302,None,Mason Phillips",
		"302,None,Leland Shaub",
		"302,None,Jacob Steward",
		"302,None,Lauren Vitale",
		"302,None,Hunter Womick",
		"303,None,Josiah Bond",
		"303,None,Austin Boyd",
		"303,None,Andrew Dutton",
		"303,None,Klajdi Hysenaj",
		"303,None,Marcus Kjar",
		"303,None,Eric Lindsay",
		"303,None,Zachary Maxwell",
		"303,None,Seth Nolte",
		"303,None,Joshua Pesek",
		"303,None,William Rix",
		"303,None,Lucia Rogers",
		"303,None,Ryan Schrick",
		"303,None,Ethan Spirer",
		"303,None,Matthew Stornello",
		"303,None,Henry Witte",
		"305,None,Benjamin Beilman",
		"305,None,Gavin Boehme",
		"305,None,Xavier Cahill",
		"305,None,Ryan Ewald",
		"305,None,Aidan Johnson",
		"305,None,Joseph Kiehne",
		"305,None,Collin McCord",
		"305,None,Craig McGowan",
		"305,None,Andrew Merkel",
		"305,None,Zachary Parr",
		"305,None,Nathaniel Randell",
		"305,None,Maddisyn Reed",
		"301,None,Tyler Rowden",
		"305,None,Michael Teroy",
		"305,None,Mason Thompson",
		"307,None,Wade Arnzen",
		"307,None,Ryan Baas",
		"307,None,Connor Bichsel",
		"307,None,Sam Calandro",
		"307,None,Allie Dingfield",
		"307,None,Dakota Duran",
		"307,None,Jack Jaeger",
		"307,None,Cole Komyati",
		"307,None,Mikayla Massie",
		"307,None,Caleb McCleary",
		"307,None,Chance Mikkelson",
		"307,None,Melissa Parker",
		"307,None,Brayden Pratt",
		"307,None,Jacob Rodeghero",
		"307,None,Emma Schouten",
		"307,None,Zachary Thomason",
		"309,None,Connor Brown",
		"309,None,Maxwell Forbes",
		"309,None,Austin Frazier",
		"309,None,Dakota Gotsch",
		"309,None,Jacob Hawkins",
		"309,None,Sydney Hayton",
		"309,None,Matthew Hoffman",
		"309,None,Nishat Mamnoon",
		"309,None,Madison McKenzie",
		"309,None,Anna Robertson",
		"309,None,Cameron Ryan",
		"309,None,Hugh Steinman",
		"309,None,Landen Stephens",
		"309,None,William Strecker",
		"309,None,Parker Wideman",
		"313,None,Hayden Cook",
		"313,None,Julianna Everett",
		"313,None,Jackson Flores",
		"313,None,Edward Henneberry",
		"313,None,Thang Le",
		"313,None,Edvin Linhorst",
		"313,None,Michael McDowell",
		"313,None,Zebedee McMenamy",
		"313,None,Otto Ottiger",
		"313,None,Rohit Ramamoorthy",
		"313,None,Christian Rosales",
		"313,None,Camron Walsh",
		"313,None,Ethan Watson",
		]

	#######BOOK KEEPING FUNCTIONS########
	def organize_responses(self,):

		#Load the secrets from .streamlit/secrets.toml
		secrets = toml.load(".streamlit/secrets.toml")
		creds_dict = secrets['connections']['gsheets']

		# Fix escaped newlines in private key
		creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

		#authenticate with gspread using dict credentials
		gc = gspread.service_account_from_dict(creds_dict)
		self.spreadsheet = gc.open_by_url(creds_dict['spreadsheet'])
		
		# Loop through each sheet (except the first)
		for sheet in self.spreadsheet.worksheets()[1:]:
			responses = sheet.get_all_values()  # list of lists

			for response in responses[1:]: 
				data = response[1].split('$*')
				assignment_id = response[0]
				student_name = str(sheet.title)
				
				if student_name not in self.student_responsebook.keys():
					self.student_responsebook[student_name] = [[assignment_id,data]]
				else:
					self.student_responsebook[student_name].append([assignment_id,data])

	def go_fix_it(self,):
		groups = 1
		for student_name, responses in self.student_responsebook.items():
			for assignment_id, data in responses:
				if assignment_id == 'Group_Lab_Selection':
					names = data[0]
					first_student = names.split(',')
					first_student = first_student[0][1:].replace("'","")
					print(first_student)

					for entry in self.students:
						number, group, name = entry.split(",", 2)  # split into 3 parts max
						if name == first_student:
							print(f'this group is in section {number}')
							data.append(number)
							data_string = ''
							data_string = f'{data[0]}$*{data[1]}$*{data[2]}'

							feedback = {
							"Survey_ID": "Group_Lab_Selection",  # or your preferred ID
							"Data": data_string
							}
							feedback_df = pd.DataFrame([feedback])
							values = [feedback_df.columns.tolist()] + feedback_df.values.tolist()

							ws = self.spreadsheet.worksheet(student_name)
							ws.update(values) 



	

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