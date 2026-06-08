import streamlit as st
import requests
import pandas as pd
import plotly.express as px

# ════════════════════════════════════════════════════════
# 1. CONFIGURATION
# ════════════════════════════════════════════════════════

API_URL = "https://datamind-ai-umrm.onrender.com"

st.set_page_config(
    page_title="DataMind AI",
    page_icon="🧠",
    layout="wide"
)

# ════════════════════════════════════════════════════════
# 2. SESSION STATE
# ════════════════════════════════════════════════════════

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ════════════════════════════════════════════════════════
# 3. CHART FUNCTION
# ════════════════════════════════════════════════════════

def create_chart(data, question=""):
    if not data or len(data) == 0:
        return None

    df = pd.DataFrame(data)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    text_cols = df.select_dtypes(include=["object"]).columns.tolist()

    if not numeric_cols or not text_cols:
        return None

    x_col = text_cols[0]
    y_col = numeric_cols[0]

    # Shorten long labels
    df[x_col] = df[x_col].astype(str).str[:30]

    question_lower = question.lower()

    # ── Line chart — for time/trend questions ─────────
    if any(word in question_lower for word in ["trend", "over time", "monthly", "yearly", "by month", "by year", "by date"]):
        fig = px.line(
            df, x=x_col, y=y_col,
            title=f"📈 {y_col.replace('_', ' ').title()} over {x_col.replace('_', ' ').title()}",
            markers=True,
            template="plotly_white"
        )

    # ── Pie chart — for distribution/share questions ──
    elif any(word in question_lower for word in ["percentage", "share", "distribution", "proportion", "breakdown"]):
        fig = px.pie(
            df, names=x_col, values=y_col,
            title=f"🥧 {y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
            color_discrete_sequence=px.colors.sequential.Blues_r,
            template="plotly_white"
        )

    # ── Horizontal bar — for rankings with long names or least/lowest questions ──
    elif len(df) > 6 or any(word in question_lower for word in ["least", "lowest", "worst", "bottom"]):
        fig = px.bar(
            df, x=y_col, y=x_col,
            orientation="h",
            title=f"📊 {y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
            color=y_col,
            color_continuous_scale="Reds",
            template="plotly_white"
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})

    # ── Vertical bar — default for top/best/highest ───
    else:
        fig = px.bar(
            df, x=x_col, y=y_col,
            title=f"📊 {y_col.replace('_', ' ').title()} by {x_col.replace('_', ' ').title()}",
            color=y_col,
            color_continuous_scale="Blues",
            template="plotly_white"
        )

    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=False,
        height=450,
        margin=dict(b=120)
    )
    return fig

# ════════════════════════════════════════════════════════
# 4. LOGIN / REGISTER PAGE
# ════════════════════════════════════════════════════════

def show_auth_page():
    st.title("🧠 DataMind AI")
    st.subheader("Intelligent Data Analyst")
    st.divider()

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login to your account")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.button("Login"):
            if username and password:
                response = requests.post(f"{API_URL}/login",
                    json={"username": username, "password": password})
                result = response.json()
                if result["success"]:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.success(result["message"])
                    st.rerun()
                else:
                    st.error(result["message"])
            else:
                st.warning("Please enter username and password.")

    with tab2:
        st.subheader("Create a new account")
        new_username = st.text_input("Choose Username", key="reg_username")
        new_password = st.text_input("Choose Password", type="password", key="reg_password")

        if st.button("Register"):
            if new_username and new_password:
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
# 5. MAIN APP PAGE
# ════════════════════════════════════════════════════════

def show_main_app():
    st.title("🧠 DataMind AI")
    st.subheader(f"Welcome, {st.session_state['username']}!")

    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()

    tab1, tab2 = st.tabs(["Ask a Question", "Query History"])

    # ── Ask Question Tab ──────────────────────────────
    with tab1:
        st.subheader("Ask anything about the data")
        question = st.text_input("Your Question",
            placeholder="e.g. What are the top 5 product categories by sales?")

        if st.button("Ask"):
            if question:
                with st.spinner("Analyzing data..."):
                    response = requests.post(f"{API_URL}/ask",
                        json={
                            "question": question,
                            "username": st.session_state["username"]
                        })
                    result = response.json()

                # ── Answer ────────────────────────────
                st.success("Answer:")
                st.write(result["answer"])

                # ── Chart ─────────────────────────────
                raw_data = result.get("raw_data", [])
                fig = create_chart(raw_data, question)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No chart available for this result.")

                # ── SQL Query ─────────────────────────
                with st.expander("See SQL Query Used"):
                    st.code(result["sql_query"], language="sql")

            else:
                st.warning("Please enter a question.")

    # ── History Tab ───────────────────────────────────
    with tab2:
        st.subheader("Your Query History")

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
# 6. APP FLOW CONTROL
# ════════════════════════════════════════════════════════

if st.session_state["logged_in"] == False:
    show_auth_page()
else:
    show_main_app()
