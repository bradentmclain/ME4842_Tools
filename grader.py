import gspread
import toml
import json
import pandas as pd
from pprint import pprint
from collections import Counter
import yaml
import stutts_picker as st
import os
import shutil

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
                student_name = str(sheet.title)
                
                if student_name not in self.student_responsebook.keys():
                    self.student_responsebook[student_name] = [[assignment_id,data]]
                else:
                    self.student_responsebook[student_name].append([assignment_id,data])



    def create_groups(self,):
        group_letters = ['A','B','C','D','E','F','G']

        #formatted as {section:Group A, Group B...}
        student_groups = {}
        grouped_students = []
        pref_responses = {}
        for student_name, responses in self.student_responsebook.items():

            for assignment_id, data in responses:
                if assignment_id == 'Group_Lab_Selection':
                    members, labs, section = data
                    members = json.loads(members.replace("'",'"'))
                    labs = json.loads(labs.replace("'",'"'))

                    if section not in student_groups.keys():
                        student_groups[section] = {}
                        student_groups[section][section+group_letters[0]] = members
                        grouped_students=grouped_students+members
                    else:
                        student_groups[section][section+group_letters[len(student_groups[section])]] = members
                        grouped_students=grouped_students+members
                    
                    pref_responses[section+group_letters[0]] = labs
                    pref_responses[section+group_letters[len(student_groups[section])]] = labs

        student_counts = Counter()

        for section in student_groups.keys():
            for group in student_groups[section].keys():
                print(f'{group}: {student_groups[section][group]}')
                students = student_groups[section][group]
                student_counts.update(students)
        
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

        self.export_groups(student_groups, not_in_groups, in_multiple_groups)


        
    
    # def assign_labs(self,):
    #         # Run picker
    #     shutil.rmtree("assignments", ignore_errors=True)
    #     os.mkdir("assignments")

    #     for section in student_groups.keys():
    #         group_data = []
    #         for group in student_groups[section].keys():
    #             group_data.append({
    #                 "Group": group,
    #                 "Electives": pref_responses[group]
    #             })

    #         groups, costs, ranks = st.process_input_and_build_costs(group_data, ['Acoustics', 'Pump', 'Tuned Mass Damper', 'Dynamic Balancing', 'Piezoelectric'], unlisted_penalty=5, seed=1)

    #         # if len(groups) > 5:
    #         #     raise SystemExit(f"Infeasible: {len(groups)} groups but only 5 one-station electives per week. Split the section or add capacity.")
    #         result, status = st.solve_ilp(groups, costs, T=2)
    #         if status != "ok":
    #             result, status = st.solve_greedy(groups, costs, T=2)

    #         st.write_output(f"assignments/{section}.xlsx", result, groups, costs, ranks, None, 5, T=2)
    #         print(json.dumps({"status": status, "total_cost": result["total_cost"], "groups": len(groups)}))


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
        

    def grade_proposal(self):

        for student_name, responses in self.student_responsebook.items():
            for assignment_id, data in responses:
                name = data[2]
                if ',' in name:
                    names = name.split(',')
                    
                    for name in names:
                        if name not in self.student_gradebook.keys():
                            self.student_gradebook[name] = [[assignment_id, data]]
                        else:
                            self.student_gradebook[name].append([assignment_id, data])
                else:
                    if name not in self.student_gradebook.keys():
                        self.student_gradebook[name] = [[assignment_id, data]]
                    else:
                        self.student_gradebook[name].append([assignment_id, data])

        individual_questions = ['dress_code', 'audience_engagement', 'body_language','enthusiasm','overall']
        group_questions = ['technical', 'efficacy', 'completeness','presentation_quality','answer_questions']
        individual_response_options = ['Substandard', 'Poor', 'Acceptable', 'Good', 'Excellent']
        response_scores = {resp: i + 1 for i, resp in enumerate(individual_response_options)}

        #structured [[student name, grade, comments]]
        self.proposal_gradebook = {}

        for student in self.student_gradebook.keys():
            ind_scores = {
                "dress_code": {"pts": 0, "total": 0},
                "audience_engagement": {"pts": 0, "total": 0},
                "body_language": {"pts": 0, "total": 0},
                "enthusiasm": {"pts": 0, "total": 0},
                "overall": {"pts": 0, "total": 0},
                "comments": []
            }
            group_scores = {
                "technical": {"pts": 0, "total": 0},
                "efficacy": {"pts": 0, "total": 0},
                "completeness": {"pts": 0, "total": 0},
                "presentation_quality": {"pts": 0, "total": 0},
                "answer_questions": {"pts": 0, "total": 0},
                "comments": []
            }
            
            for assignment_id, data in self.student_gradebook[student]:
                if assignment_id == 'Proposal_Individual':
                    #data = reviewer name, reviewer weight, reviewee name, dress score, engagement score, body language score, enthusiasm score, speaking score, comments
                    weight = float(data[1])
                    scores = [response_scores.get(x, x) for x in data[3:8]]
                    comments = data[8]
                    for q, s in zip(individual_questions, scores):
                        ind_scores[q]["pts"]   += s * weight
                        ind_scores[q]["total"] += 5 * weight
                    if comments != '':
                        ind_scores['comments'].append(comments)
                elif assignment_id == 'Proposal_Group':
                    #data = Reviewer name, weight, group members, Group code,comments, techincal, efficacy, comepleteness, quality, questions
                    weight = float(data[1])
                    scores = [float(x) for x in data[5:]]
                    comments = data[4]
                    group_name = data[3]
                    for q, s in zip(group_questions, scores):
                        group_scores[q]["pts"]   += s * weight
                        group_scores[q]["total"] += 10 * weight
                    if comments != '':
                        group_scores['comments'].append(comments)

            individual_score_normalized = sum(v["pts"] for v in ind_scores.values() if isinstance(v, dict)) / sum(v["total"] for v in ind_scores.values() if isinstance(v, dict))
            group_score_normalized = sum(v["pts"] for v in group_scores.values() if isinstance(v, dict)) / sum(v["total"] for v in group_scores.values() if isinstance(v, dict))
            overall_score = (individual_score_normalized*25) + (group_score_normalized *10)


            text_feedback = f"""
            ---------------------------------------------------
            Individual Scores: {student}
            ---------------------------------------------------
            Dress Code: {(ind_scores["dress_code"]["pts"] / ind_scores["dress_code"]["total"] * 100):.2f}%
            Audience Engagement: {(ind_scores["audience_engagement"]["pts"] / ind_scores["audience_engagement"]["total"] * 100):.2f}%
            Body Language: {(ind_scores["body_language"]["pts"] / ind_scores["body_language"]["total"] * 100):.2f}%
            Enthusiasm: {(ind_scores["enthusiasm"]["pts"] / ind_scores["enthusiasm"]["total"] * 100):.2f}%
            Speaking: {(ind_scores["overall"]["pts"] / ind_scores["overall"]["total"] * 100):.2f}%
            
            Individual Score: {individual_score_normalized*100:.2f}%
            Individual Points: {individual_score_normalized*25:.2f} / 25

            Inidvidual Feedback Recieved: {"\n".join(ind_scores["comments"])}

            ---------------------------------------------------
            Group Scores: {group_name}
            ---------------------------------------------------
            Technical: {(group_scores["technical"]["pts"] / group_scores["technical"]["total"] * 100):.2f}%
            Efficacy: {(group_scores["efficacy"]["pts"] / group_scores["efficacy"]["total"] * 100):.2f}%
            Completeness: {(group_scores["completeness"]["pts"] / group_scores["completeness"]["total"] * 100):.2f}%
            Presentation Quality: {(group_scores["presentation_quality"]["pts"] / group_scores["presentation_quality"]["total"] * 100):.2f}%
            Ability to Answer Questions: {(group_scores["answer_questions"]["pts"] / group_scores["answer_questions"]["total"] * 100):.2f}%
            
            Group Score: {group_score_normalized*100}%
            Group Points: {group_score_normalized*10} / 10
            
            Group Feedback Recieved: {"\n".join(group_scores["comments"])}

            ---------------------------------------------------
            Final Assignment Grade
            ---------------------------------------------------
            Group Score + Individual Score = Overall Score
            
            {individual_score_normalized*25:.2f} + {group_score_normalized*10:.2f}  = {overall_score}/35 
            """

            self.proposal_gradebook[student] = [overall_score,text_feedback]
        return self.proposal_gradebook



if __name__ == "__main__":
    grad = Grader()
    grad.organize_responses()
    grad.create_groups()

    # for grade in proposal_grades:
    # 	print(grade[2])
    #for student in grad.student_gradebook.keys():
        # print(student,grad.student_gradebook[student])
        # print('\n')