import streamlit as st
from streamlit_gsheets import GSheetsConnection
import time
import random
import string


st.title("✅ Google Sheets Auth Test")

# Initialize connection
conn = st.connection("gsheets", type=GSheetsConnection)

# Function to load the sheet
@st.cache_data(show_spinner=False)
def load_sheet():
	start_read = time.time()
	data = conn.read(worksheet="Data")
	st.write(f'📥 Read time: {time.time()-start_read:.2f} seconds')
	return data

# Button to reload data
if st.button("🔄 Refresh from Sheet"):
	st.cache_data.clear()
import pandas as pd

# Create an empty DataFrame with 10 columns and 6 rows
blank = pd.DataFrame(columns=[f"col{i+1}" for i in range(10)], index=range(6))

# Load the data
try:
	df = load_sheet()
	st.success("✅ Successfully loaded sheet!")
	st.dataframe(df)

	# Update an example value
	st.write("Name at index 1:", df['name'][1])
	df.at[1, 'name'] = 'Braden'
	st.write("Updated name at index 1:", df['name'][1])

	if st.button("⬆️ Update Sheet"):
		start_write = time.time()
		conn.update(worksheet="Data", data=df)
		st.success(f"✅ Sheet updated successfully! 🕒 {time.time()-start_write:.2f} seconds")

except Exception as e:
	st.error(f"❌ Failed to connect or read data:\n\n{e}")

if st.button("🆕 Create Randomly Named Worksheet"):
	new_name = ''.join(random.choices(string.ascii_uppercase, k=3))
	try:
		conn.create(worksheet=new_name, data=blank)  # create empty sheet
		st.success(f"✅ Created new worksheet: `{new_name}`")
	except Exception as e:
		st.error(f"❌ Failed to create worksheet:\n\n{e}")

sh = conn._instance._open_spreadsheet()

worksheets = sh.worksheets()
st.header('All Available worksheets:')
for worksheet in worksheets:
	st.write(worksheet.title)
