import streamlit as st
import requests
import pandas as pd

BACKEND_URL = "https://parkinson-project-1.onrender.com"
st.set_page_config(page_title="Parkinson's AI System", page_icon="🧠")

if 'token' not in st.session_state:
    st.session_state.token = None
if 'role' not in st.session_state:
    st.session_state.role = None


def login_user(username, password):
    try:
        data = {"username": username, "password": password}
        response = requests.post(f"{BACKEND_URL}/token", data=data)
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.token = token_data["access_token"]
            st.session_state.role = token_data["role"]  # <--- Save Role
            st.success(f"Login successful as {token_data['role'].upper()}")
            st.rerun()
        else:
            st.error("Invalid credentials")
    except Exception as e:
        st.error(f"Error: {e}")


def register_user(username, password):
    try:
        # We send the role to the backend
        data = {"username": username, "password": password}
        response = requests.post(f"{BACKEND_URL}/register", data=data)
        if response.status_code == 200:
            st.success("Account created! Please login.")
        else:
            st.error(response.json()['detail'])
    except Exception as e:
        st.error(f"Error: {e}")


# --- DOCTOR DASHBOARD ---
def doctor_dashboard():
    st.sidebar.title("Doctor Menu")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.rerun()

    tab1, tab2 = st.tabs(["New Diagnosis", "Patient History"])

    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    with tab1:
        st.header("New Diagnosis")
        p_name = st.text_input("Patient Name")
        p_age = st.number_input("Age", 0, 120)
        uploaded_file = st.file_uploader("Upload Spiral/Wave Image", type=["jpg", "png"])

        if st.button("Analyze"):
            if uploaded_file:
                files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                data = {"patient_name": p_name, "patient_age": p_age}
                res = requests.post(f"{BACKEND_URL}/predict", files=files, data=data, headers=headers)
                if res.status_code == 200:
                    r = res.json()
                    st.success(f"Result: {r['prediction']}")
                    st.info(f"Confidence: {r['confidence']}%")

    with tab2:
        st.header("History")
        res = requests.get(f"{BACKEND_URL}/history", headers=headers)
        if res.status_code == 200:
            st.dataframe(pd.DataFrame(res.json()))


# --- ADMIN DASHBOARD (Matches your Diagrams) ---
def admin_dashboard():
    st.sidebar.title("Admin Menu")
    if st.sidebar.button("Logout"):
        st.session_state.token = None
        st.rerun()

    st.title("System Statistics")

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    res = requests.get(f"{BACKEND_URL}/admin/stats", headers=headers)

    if res.status_code == 200:
        data = res.json()

        col1, col2 = st.columns(2)
        col1.metric("Total Users", data['total_users'])
        col2.metric("Total Predictions", data['total_predictions'])

        st.divider()
        st.subheader("Disease Distribution")
        chart_data = pd.DataFrame({
            "Category": ["Healthy", "Parkinson"],
            "Count": [data['healthy_cases'], data['parkinson_cases']]
        })
        st.bar_chart(chart_data.set_index("Category"))
    else:
        st.error("Failed to fetch stats.")


# --- MAIN APP ---
if not st.session_state.token:
    st.title("Parkinson's AI System")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            login_user(u, p)

    with tab2:
        u_reg = st.text_input("New Username")
        p_reg = st.text_input("New Password", type="password")
        # Allow selecting role for demo purposes
        #role = st.selectbox("Role", ["doctor", "admin"])
        if st.button("Register"):
            register_user(u_reg, p_reg)
else:
    # ROUTING BASED ON ROLE
    if st.session_state.role == "admin":
        admin_dashboard()
    else:
        doctor_dashboard()