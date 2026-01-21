# ME4842_Tools
Repository for writing ME4842 surveys, grading surveys based on reponder input, and uploading grades to Canvas.

Current ME4842 Assignments available via Streamlit:
- Group Creation (group_creation.py)
- Proposal Presentation (auth_proposal_survey.py)
- Midterm Peer Evaluation (midterm_peer_evaluation.py)
- Poster Symposium (poster_symposium.py)
- Final Peer Evaluation (final_peer_evaluation.py)

### Overall Structure of Repository
This repository is structured to meet the needs of ME4842. It contains many modular tools that can be easily used for survey creation and Canvas grading automation in other courses. The basic structure is as follows:
- Surveys are hosted online or locally through Streamlit, an open-source Python framework for data collection.
- All data from surveys is stored in Firebase Realtime Database, a NoSql cloud database from Google.
- Grader.py pulls data from Firebase and grades desired assignments.
- Upload_Grades.py utilizes Grader.py and canvas_tools.py to score assignments and upload the scores to Canvas.
- A single "secrets.toml" file contains Canvas, Firebase, and OAuth API Keys as well as organizational student data. Student data kept in this file is not sensitive and includes [Section, Group, Name, Email.]

## Setup Guide
Before using tools in this reposityor, the following setup steps must be taken.

1. 

## Useage Guide
To 

### Survey Useage
The following guide will walk you through the steps of first time setup and useage of this repository. 


In order to locally host the streamlit survey, you must first install all neccessary dependencies.

`pip install -r requirements.txt`

You must also create a secrets.toml file containing neccessary configuration information for the survey.  This includes [connections.gsheets] information for the database connection and [class_list] data for creating the course survey. This file should be stored in ./.streamlit/secrets.toml at the root of your directory. More details will be posted here in the future. **TODO:** Come back and add instructions for connecting to google sheets and for getting class list from canvas tools. Also add layout for secrets file.

After installing dependencies you can launch the application with the following:

`streamlit run example_survey.py`

In order to host the survey with streamlit's community cloud, visit https://streamlit.io/cloud. From here you can create an account and launch your survey via their "Create app" tool. You will need to link this github repository and add a pointer to the desired survey python file. The secrets file for this can be added in the app settings.

### Grader Useage

The course grader is intended to be modular. All course data is stored in the form of (Assignment ID,
Assignment Data), so that the grader can grade many different assignments. The organize_responses function will collect all data from the student database and organize it into a dictionary containing responses each student received, along with their assignment data. Feed this data into the grader for any desired function.

### Canvas API Useage

The Canvas API is full of useful calls to manipulate your course and query class data. In order to use this script, you need to add a configuration file of canvas_secrets.toml into ./.canvas/canvas_secrets.toml within your root directory. The secrets file should contain your personal API key along with the umsystem api url.  Optionally, you can add the course ID into the secrets file. **TODO:** Add layout for secrets file.


Feel free to contact Braden McLain (btmywv@umsystem.edu) with any questions.

