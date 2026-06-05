import uvicorn
import sqlite3
import hashlib
import pandas as pd
import os
from sqlalchemy import create_engine
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

DB_PATH = "datamind.db"
DB_URL = f"sqlite:///{DB_PATH}"

def setup_database():
    engine = create_engine(DB_URL)

    customers    = pd.read_csv("olist_customers_dataset.csv")
    orders       = pd.read_csv("olist_orders_dataset.csv")
    order_items  = pd.read_csv("olist_order_items_dataset.csv")
    products     = pd.read_csv("olist_products_dataset.csv")
    payments     = pd.read_csv("olist_order_payments_dataset.csv")
    translation  = pd.read_csv("product_category_name_translation.csv")

    products = products.merge(translation, on="product_category_name", how="left")
    products["product_category_name"] = products["product_category_name_english"].fillna(products["product_category_name"])
    products = products.drop(columns=["product_category_name_english"])

    with engine.connect() as conn:
        customers.to_sql("customers",    conn, if_exists="replace", index=False)
        orders.to_sql("orders",          conn, if_exists="replace", index=False)
        order_items.to_sql("order_items",conn, if_exists="replace", index=False)
        products.to_sql("products",      conn, if_exists="replace", index=False)
        payments.to_sql("payments",      conn, if_exists="replace", index=False)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)
    cursor.execute("""
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

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY")
)

# ════════════════════════════════════════════════════════
# 3. AGENT STATE
# ════════════════════════════════════════════════════════

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

def schema_reader(state: AgentState) -> AgentState:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        schema_info = ""
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            schema_info += f"Table: {table_name}\nColumns: {', '.join(column_names)}\n\n"
        conn.close()
        return {**state, "schema": schema_info}
    except Exception as e:
        return {**state, "error": str(e)}

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

def sql_executor(state: AgentState) -> AgentState:
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            results = pd.read_sql(state["sql_query"], conn)
        raw_results = results.to_string(index=False)
        return {**state, "raw_results": raw_results}
    except Exception as e:
        return {**state, "error": str(e)}

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

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
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

graph = StateGraph(AgentState)
graph.add_node("schema_reader",      schema_reader)
graph.add_node("sql_generator",      sql_generator)
graph.add_node("sql_executor",       sql_executor)
graph.add_node("results_formatter",  results_formatter)
graph.add_edge("schema_reader",      "sql_generator")
graph.add_edge("sql_generator",      "sql_executor")
graph.add_edge("sql_executor",       "results_formatter")
graph.add_edge("results_formatter",  END)
graph.set_entry_point("schema_reader")
pipeline = graph.compile()
print("✅ LangGraph pipeline ready!")

# ════════════════════════════════════════════════════════
# 6. AUTHENTICATION
# ════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username: str, password: str) -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, ?)
        """, (username, hash_password(password), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"User {username} registered successfully!"}
    except:
        return {"success": False, "message": "Username already exists."}

def login_user(username: str, password: str) -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username FROM users
            WHERE username = ? AND password_hash = ?
        """, (username, hash_password(password)))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"success": True, "message": f"Welcome back {username}!", "username": username}
        else:
            return {"success": False, "message": "Wrong username or password."}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ════════════════════════════════════════════════════════
# 7. FASTAPI APP
# ════════════════════════════════════════════════════════

app = FastAPI(title="DataMind AI", description="Intelligent Data Analyst API")

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str
    username: str

@app.post("/register")
def register(request: RegisterRequest):
    return register_user(request.username, request.password)

@app.post("/login")
def login(request: LoginRequest):
    return login_user(request.username, request.password)

@app.post("/ask")
def ask_question(request: QuestionRequest):
    result = pipeline.invoke({
        "question":     request.question,
        "username":     request.username,
        "schema":       "",
        "sql_query":    "",
        "raw_results":  "",
        "final_answer": "",
        "error":        ""
    })
    return {
        "question":  request.question,
        "answer":    result["final_answer"],
        "sql_query": result["sql_query"]
    }

@app.get("/history/{username}")
def get_history(username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT question, answer, timestamp
        FROM query_history
        WHERE username = ?
        ORDER BY timestamp DESC
    """, (username,))
    rows = cursor.fetchall()
    conn.close()
    return [{"question": r[0], "answer": r[1], "timestamp": r[2]} for r in rows]

# ════════════════════════════════════════════════════════
# 8. RUN SERVER
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
