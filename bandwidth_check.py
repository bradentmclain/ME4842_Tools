import json
import streamlit as st
from firebase_admin import credentials, db
import firebase_admin



cred = dict(st.secrets["firebase_creds"])
cred = credentials.Certificate(cred)
firebase_admin.initialize_app(cred, {"databaseURL": "https://fs2025-me4842-default-rtdb.firebaseio.com/"})

snap = db.reference("Proposal_Response").get()
payload_bytes = len(json.dumps(snap, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
print(f"~{payload_bytes} bytes downloaded (payload only)")