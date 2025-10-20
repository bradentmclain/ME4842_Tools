import streamlit as st

ALLOWED_EMAILS = {
    "you@mst.edu",
    "ta1@mst.edu",
    "btmywv@umsystem.edu",
}

def login_screen():
    st.header("This app is private.")
    st.subheader("Please log in.")
    st.button("Log in with Google", on_click=st.login)

def is_allowed(email: str) -> bool:
    return bool(email) and email.lower() in {e.lower() for e in ALLOWED_EMAILS}

if st.user.is_logged_in:
    # Safely extract claims (st.user is dict-like)
    user_dict = dict(st.user)
    email = user_dict.get("email")
    name = user_dict.get("name", "User")

    if is_allowed(email):
        st.success(f"You are successfully logged in, {name}.")
        st.write("Welcome to the private area.")
        # ... your protected content here ...
    else:
        st.error(f"Access denied for {email or 'unknown user'}.")
        st.button("Log out", on_click=st.logout)
else:
    login_screen()
