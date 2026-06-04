
import uvicorn
import sqlite3
import hashlib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict
from datetime import datetime

# ════════════════════════════════════════════════════════
# 1. DATABASE SETUP
# ════════════════════════════════════════════════════════
# Connect to SQLite database and load all CSV data

def setup_database():
    conn = sqlite3.connect("datamind.db")

    # Load Olist CSV files into database
    customers = pd.read_csv("olist_customers_dataset.csv")
    orders = pd.read_csv("olist_orders_dataset.csv")
    order_items = pd.read_csv("olist_order_items_dataset.csv")
    products = pd.read_csv("olist_products_dataset.csv")
    payments = pd.read_csv("olist_order_payments_dataset.csv")
    translation = pd.read_csv("product_category_name_translation.csv")

    # Fix Portuguese product names to English
    products = products.merge(translation, on="product_category_name", how="left")
    products["product_category_name"] = products["product_category_name_english"].fillna(products["product_category_name"])
    products = products.drop(columns=["product_category_name_english"])

    # Save all tables to database
    customers.to_sql("customers", conn, if_exists="replace", index=False)
    orders.to_sql("orders", conn, if_exists="replace", index=False)
    order_items.to_sql("order_items", conn, if_exists="replace", index=False)
    products.to_sql("products", conn, if_exists="replace", index=False)
    payments.to_sql("payments", conn, if_exists="replace", index=False)

    # Create users table — stores registered users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)

    # Create query history table — saves every question and answer
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            question TEXT,
            sql_query TEXT,
            answer TEXT,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database ready!")

setup_database()

# ════════════════════════════════════════════════════════
# 2. LLM SETUP
# ════════════════════════════════════════════════════════
# Initialize Groq LLM — used by SQL Generator and Results Formatter

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key="YOUR_GROQ_API_KEY"
)

# ════════════════════════════════════════════════════════
# 3. AGENT STATE
# ════════════════════════════════════════════════════════
# Shared notebook passed between all 4 agents

class AgentState(TypedDict):
    question: str
    username: str
    schema: str
    sql_query: str
    raw_results: str
    final_answer: str
    error: str

# ════════════════════════════════════════════════════════
# 4. THE 4 AGENTS
# ════════════════════════════════════════════════════════

# ── Agent 1 — Schema Reader ───────────────────────────
# Reads database structure so SQL Generator knows what exists
def schema_reader(state: AgentState) -> AgentState:
    try:
        conn = sqlite3.connect("datamind.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        schema_info = ""
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            schema_info += f"Table: {table_name}\n"
            schema_info += f"Columns: {', '.join(column_names)}\n\n"
        conn.close()
        return {**state, "schema": schema_info}
    except Exception as e:
        return {**state, "error": str(e)}

# ── Agent 2 — SQL Generator ───────────────────────────
# Converts user English question into proper SQL query
def sql_generator(state: AgentState) -> AgentState:
    try:
        prompt = f"""
        You are an expert SQL generator.
        Here is the database schema:
        {state["schema"]}
        The user asked: {state["question"]}
        Write a proper SQLite SQL query to answer this question.
        Return ONLY the SQL query. Nothing else. No explanation. No markdown.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        sql_query = response.content.strip()
        return {**state, "sql_query": sql_query}
    except Exception as e:
        return {**state, "error": str(e)}

# ── Agent 3 — SQL Executor ────────────────────────────
# Runs the SQL query on the database and returns raw results
def sql_executor(state: AgentState) -> AgentState:
    try:
        conn = sqlite3.connect("datamind.db")
        results = pd.read_sql(state["sql_query"], conn)
        conn.close()
        raw_results = results.to_string(index=False)
        return {**state, "raw_results": raw_results}
    except Exception as e:
        return {**state, "error": str(e)}

# ── Agent 4 — Results Formatter ──────────────────────
# Converts raw results into friendly answer and saves to history
def results_formatter(state: AgentState) -> AgentState:
    try:
        prompt = f"""
        You are a helpful data analyst assistant.
        The user asked: {state["question"]}
        Here are the raw results: {state["raw_results"]}
        Write a clear, friendly, professional answer.
        Do not mention SQL or technical details.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        final_answer = response.content.strip()

        # Save question and answer to query history
        conn = sqlite3.connect("datamind.db")
        conn.execute("""
            INSERT INTO query_history (username, question, sql_query, answer, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (
            state["username"],
            state["question"],
            state["sql_query"],
            final_answer,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        return {**state, "final_answer": final_answer}
    except Exception as e:
        return {**state, "error": str(e)}

# ════════════════════════════════════════════════════════
# 5. LANGGRAPH PIPELINE
# ════════════════════════════════════════════════════════
# Connect all 4 agents in sequence

graph = StateGraph(AgentState)
graph.add_node("schema_reader", schema_reader)
graph.add_node("sql_generator", sql_generator)
graph.add_node("sql_executor", sql_executor)
graph.add_node("results_formatter", results_formatter)
graph.add_edge("schema_reader", "sql_generator")
graph.add_edge("sql_generator", "sql_executor")
graph.add_edge("sql_executor", "results_formatter")
graph.add_edge("results_formatter", END)
graph.set_entry_point("schema_reader")
pipeline = graph.compile()
print("✅ LangGraph pipeline ready!")

# ════════════════════════════════════════════════════════
# 6. AUTHENTICATION
# ════════════════════════════════════════════════════════

# Hash password before saving — never store plain text passwords
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# Register new user — saves username and hashed password
def register_user(username: str, password: str) -> dict:
    try:
        conn = sqlite3.connect("datamind.db")
        conn.execute("""
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
        """, (username, hash_password(password),
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"User {username} registered successfully!"}
    except:
        return {"success": False, "message": "Username already exists."}

# Login user — checks username and password against database
def login_user(username: str, password: str) -> dict:
    try:
        conn = sqlite3.connect("datamind.db")
        result = pd.read_sql("""
            SELECT user_id, username FROM users
            WHERE username = ? AND password_hash = ?
        """, conn, params=(username, hash_password(password)))
        conn.close()
        if len(result) > 0:
            return {"success": True, "message": f"Welcome back {username}!",
                    "username": username}
        else:
            return {"success": False, "message": "Wrong username or password."}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ════════════════════════════════════════════════════════
# 7. FASTAPI APP
# ════════════════════════════════════════════════════════

app = FastAPI(title="DataMind AI", description="Intelligent Data Analyst API")

# ── Request Models ────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str
    username: str

# ── Register Endpoint ─────────────────────────────────
# Creates a new user account
@app.post("/register")
def register(request: RegisterRequest):
    return register_user(request.username, request.password)

# ── Login Endpoint ────────────────────────────────────
# Verifies username and password
@app.post("/login")
def login(request: LoginRequest):
    return login_user(request.username, request.password)

# ── Ask Question Endpoint ─────────────────────────────
# Runs full 4 agent pipeline and returns answer
@app.post("/ask")
def ask_question(request: QuestionRequest):
    result = pipeline.invoke({
        "question": request.question,
        "username": request.username,
        "schema": "",
        "sql_query": "",
        "raw_results": "",
        "final_answer": "",
        "error": ""
    })
    return {
        "question": request.question,
        "answer": result["final_answer"],
        "sql_query": result["sql_query"]
    }

# ── History Endpoint ──────────────────────────────────
# Returns query history for a specific user
@app.get("/history/{username}")
def get_history(username: str):
    conn = sqlite3.connect("datamind.db")
    history = pd.read_sql("""
        SELECT question, answer, timestamp
        FROM query_history
        WHERE username = ?
        ORDER BY timestamp DESC
    """, conn, params=(username,))
    conn.close()
    return history.to_dict(orient="records")

# ════════════════════════════════════════════════════════
# 8. RUN SERVER
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
