
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# ════════════════════════════════════════════════════════
# 1. CONFIGURATION
# ════════════════════════════════════════════════════════
# FastAPI backend URL — replace with your Render URL later
API_URL = "https://earshot-cube-shrapnel.ngrok-free.dev"

# Page setup
st.set_page_config(
    page_title="DataMind AI",
    page_icon="🧠",
    layout="wide"
)

# ════════════════════════════════════════════════════════
# 2. SESSION STATE
# ════════════════════════════════════════════════════════
# Remember if user is logged in or not

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ════════════════════════════════════════════════════════
# 3. LOGIN / REGISTER PAGE
# ════════════════════════════════════════════════════════
# Only shown when user is NOT logged in

def show_auth_page():
    st.title("🧠 DataMind AI")
    st.subheader("Intelligent Data Analyst")
    st.divider()

    # Two tabs — Login and Register
    tab1, tab2 = st.tabs(["Login", "Register"])

    # ── Login Tab ─────────────────────────────────────
    with tab1:
        st.subheader("Login to your account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            if username and password:
                # Call FastAPI login endpoint
                response = requests.post(f"{API_URL}/login",
                    json={"username": username, "password": password})
                result = response.json()

                if result["success"]:
                    # Save login state
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success(result["message"])
                    st.rerun()
                else:
                    st.error(result["message"])
            else:
                st.warning("Please enter username and password.")

    # ── Register Tab ──────────────────────────────────
    with tab2:
        st.subheader("Create a new account")
        new_username = st.text_input("Choose Username", key="reg_username")
        new_password = st.text_input("Choose Password", type="password", key="reg_password")

        if st.button("Register"):
            if new_username and new_password:
                # Call FastAPI register endpoint
                response = requests.post(f"{API_URL}/register",
                    json={"username": new_username, "password": new_password})
                result = response.json()

                if result["success"]:
                    st.success(result["message"] + " Please login now.")
                else:
                    st.error(result["message"])
            else:
                st.warning("Please fill in all fields.")

# ════════════════════════════════════════════════════════
# 4. MAIN APP PAGE
# ════════════════════════════════════════════════════════
# Only shown when user IS logged in

def show_main_app():
    # ── Header ────────────────────────────────────────
    st.title("🧠 DataMind AI")
    st.subheader(f"Welcome, {st.session_state['username']}!")

    # Logout button
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()

    # ── Two tabs — Ask and History ─────────────────────
    tab1, tab2 = st.tabs(["Ask a Question", "Query History"])

    # ── Ask Question Tab ──────────────────────────────
    with tab1:
        st.subheader("Ask anything about the data")
        question = st.text_input("Your Question",
            placeholder="e.g. What are the top 5 product categories by sales?")

        if st.button("Ask"):
            if question:
                with st.spinner("Analyzing data..."):
                    # Call FastAPI ask endpoint
                    response = requests.post(f"{API_URL}/ask",
                        json={
                            "question": question,
                            "username": st.session_state["username"]
                        })
                    result = response.json()

                # Show answer
                st.success("Answer:")
                st.write(result["answer"])

                # Show SQL query used
                with st.expander("See SQL Query Used"):
                    st.code(result["sql_query"], language="sql")

                # ── Data Visualization ─────────────────
                # Try to create a chart from the results
                try:
                    # Call history to get latest result for chart
                    history_response = requests.get(
                        f"{API_URL}/history/{st.session_state['username']}")
                    history_data = history_response.json()

                    if history_data:
                        latest = history_data[0]
                        st.info("💡 Tip: Check Query History tab to see all your past questions.")
                except:
                    pass
            else:
                st.warning("Please enter a question.")

    # ── History Tab ───────────────────────────────────
    with tab2:
        st.subheader("Your Query History")

        # Call FastAPI history endpoint
        response = requests.get(
            f"{API_URL}/history/{st.session_state['username']}")
        history = response.json()

        if history:
            for item in history:
                with st.expander(f"Q: {item['question']} — {item['timestamp']}"):
                    st.write(item["answer"])
        else:
            st.info("No history yet. Ask your first question!")

# ════════════════════════════════════════════════════════
# 5. APP FLOW CONTROL
# ════════════════════════════════════════════════════════
# Show login page or main app based on login status

if st.session_state["logged_in"] == False:
    show_auth_page()
else:
    show_main_app()
