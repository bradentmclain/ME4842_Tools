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
- A `secrets.toml` file contains  Firebase, and OAuth API Keys as well as organizational student data. Student data kept in this file is not sensitive and includes [Section, Group, Name, Email.] A seperate `canvas_secrets.toml` file stores Canvas API key information.

## Setup Guide
Before using tools in this repository, the following setup steps must be taken.

1. Create a personal Canvas API key and add it to secrets.toml.
2. Create a Firebase Realtime Database for the project. Add the Firebase service account key (JSON) to secrets.toml.
3. Create a Streamlit Community Cloud account. Run online surveys by linking this Github repo to your account. Run local surveys by installing `requirements.txt`.
4. Create a Google OAuth client and add the client secret to secrets.toml. You will also need to allow redirect URIs with links for all applications.

### Create Canvas API key
1. Log into your Canvas account. Open account settings.
2. Under "Approved Integrations" select "New Token".  Add name and desired expiration date.
3. Generate the token. This will be the only time you can see the token here. Immidiatley move the key into the `./.canvas/canvas_secrets.toml` file in the [canvas] section.
***Note this key should be securely saved and never commited to a github page. It should be treated as a password.

### Create Firebase Realtime Database
1. Go to the firebase console https://console.firebase.google.com/ and sign in with your desired Google account.
2. Create a new firebase project by following prompts. This project will store one database.
3. After the project has been created you will be taken to Firebase project home. On the "Product Categories" tab select "Build" > "Realtime Database" > "Create Database"
4. After the database has been created copy the reference url and add it into `./.secrets/secrets.toml` file in the [database_url] section.
5. Open "Project settings". Under the "Service accounts" tab, select "Python" as the firebase admin SDK.
6. Select "Generate new private key" and download the .JSON key file. Move this file into the "./.secrets/secrets.toml" file in the [firebase_creds] section.
***Note this key should be securely saved and never commited to a github page. It should be treated as a password.

### Create Streamlit Community Cloud Account
1. Go to the Streamlit Community Cloud site https://streamlit.io/cloud and authenticate with your github account. This is required to launch web applications.
2. Approve streamlit access to the ME4842_Tools repository.

### Create OAuth Client
1. Open Google Cloud Console https://console.cloud.google.com/apis/credentials and accept terms of service. Create a project.
2. Configure "OAuth consent screen" with desired contact information and organization requirements.
3. Select "Create credentials" > "OAuth client ID". The application type is a "Web application".
4. Under "Authorized Redirect URIs" add the callback URIs from each streamlit web app you create. This can be done throughout the semester as you create new apps. The URIs take the form <https://my-app.streamlit.app//oauth2callback>. To run locally use <http://localhost:8501/oauth2callback>. You will need to add this redirect URI into the web app's corresponding "./.secrets/secrets.toml" file. Each web based streamlit application has its own secrets.toml file.
5. Create the credentials and the copy the "Client ID" and "Client Secret". Paste them both into the `./.secrets/secrets.toml` in the [auth] section.

## Useage Guide
In order to use this repository for ME4842 follow the steps below. You can use this codebase to follow similar steps for other courses as well.

0. Follow the setup guide above to create all neccesary accounts and secrets files.

#### First Week Group Creation and Lab Assignment
1. Create student list and add to `./.secrets/secrets.toml`.
    1. Update COURSE_ID within `./.canvas/canvas_secrets.toml` file to reflect this semester's Canvas course ID. This is a 6 digit number that can be found in the course link. Example: https://umsystem.instructure.com/courses/######
    2. Use `canvas_tools.py` to print student data for secrets file. Follow instructions and paste into `./.secrets/secrets.toml` file for running locally. 

       ```bash
        python canvas_tools.py secrets
 
4. Launch streamlit survey.
    1. To launch any streamlit survey locally, in this case the group creation survey, run the following command:

        ```bash
        `streamlit run group_creation.py`

    2. To launch the streamlit survey through community cloud, first open up the developer's console. https://share.streamlit.io/
    3. Select "Create app" > "Deploy public app from Github" and then fill in neccesary information. The "Main file path" needs to point to your desired survey in the Github repo.
    4. Select "Advanced settings". Use Python3.13.  Copy your local `secrets.toml` file and paste into encrypted secrets enviroment.
    5. Select "Deploy" when you are ready to launch the survey.  Note survey will sleep after 48 hours of inactivity.  You can relaunch from the developers console at any time.
    6. After students have filled out the survey you can create the `groups.yml` file. This file is used to assign group in Canvas and to assign lab selections for the semester.  Create this file with the following command:

       ```bash
        `python grader.py groups_yml`
       
    7. This file should be treated similarly to a .git conflict. There are two types of conflicts that this file will highlight, "Students in multiple groups" and "Students not in groups". Manually alter the file to remove students in multiple groups and add students who are missing. "Students in multiple groups" must be resolved prior to uploading groups to Canvas. To create this file type the following command in root.
    8. Once the `groups.yml` has been resolved, create groups and add students with the following command:

        ```bash
        `python canvas_tools.py upload_groups`
        
    8. In order to assign student lab groups use the following command.  This command uses `stutts_picker.py` to evaluate the students desired lab selection and select the optimal (least negative) choice. Output from this will be saved in `./lab_assignments` and are in the form .xlsx.

          ```bash
        `python grader.py assign_labs`

#### Mid-Semester Presentation Survey Feedback
1.

<!-- 



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
-->

Feel free to contact Braden McLain (btmywv@umsystem.edu) with any questions.

