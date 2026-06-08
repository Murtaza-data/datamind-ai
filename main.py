import uvicorn
import hashlib
import pandas as pd
import os
import json
from sqlalchemy import create_engine, text
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

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

def setup_database():
    customers   = pd.read_csv("olist_customers_dataset.csv")
    orders      = pd.read_csv("olist_orders_dataset.csv")
    order_items = pd.read_csv("olist_order_items_dataset.csv")
    products    = pd.read_csv("olist_products_dataset.csv")
    payments    = pd.read_csv("olist_order_payments_dataset.csv")
    translation = pd.read_csv("product_category_name_translation.csv")

    products = products.merge(translation, on="product_category_name", how="left")
    products["product_category_name"] = products["product_category_name_english"].fillna(products["product_category_name"])
    products = products.drop(columns=["product_category_name_english"])

    with engine.connect() as conn:
        customers.to_sql("customers",    conn, if_exists="replace", index=False)
        orders.to_sql("orders",          conn, if_exists="replace", index=False)
        order_items.to_sql("order_items",conn, if_exists="replace", index=False)
        products.to_sql("products",      conn, if_exists="replace", index=False)
        payments.to_sql("payments",      conn, if_exists="replace", index=False)

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS query_history (
                id SERIAL PRIMARY KEY,
                username TEXT,
                question TEXT,
                sql_query TEXT,
                answer TEXT,
                timestamp TEXT
            )
        """))
        conn.commit()
    print("✅ Database ready!")

setup_database()

# ════════════════════════════════════════════════════════
# 2. LLM SETUP
# ════════════════════════════════════════════════════════

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
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
    raw_data: str        
    final_answer: str
    error: str
# ════════════════════════════════════════════════════════
# 4. THE 4 AGENTS
# ════════════════════════════════════════════════════════

def schema_reader(state: AgentState) -> AgentState:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """))
            tables = result.fetchall()
            schema_info = ""
            for table in tables:
                table_name = table[0]
                col_result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns
                    WHERE table_name = :table_name AND table_schema = 'public'
                """), {"table_name": table_name})
                columns = col_result.fetchall()
                column_names = [col[0] for col in columns]
                schema_info += f"Table: {table_name}\nColumns: {', '.join(column_names)}\n\n"
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
        Write a proper PostgreSQL SQL query to answer this question.
        Always include LIMIT 20 at the end unless the user asks for a specific number.
        Return ONLY the SQL query. Nothing else. No explanation. No markdown.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        sql_query = response.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        return {**state, "sql_query": sql_query}
    except Exception as e:
        return {**state, "error": str(e)}

def sql_executor(state: AgentState) -> AgentState:
    try:
        with engine.connect() as conn:
            results = pd.read_sql(state["sql_query"], conn)
        results = results.head(50)
        raw_results = results.to_string(index=False)
        raw_data = results.to_json(orient="records")   
        return {**state, "raw_results": raw_results, "raw_data": raw_data}  
    except Exception as e:
        return {**state, "error": str(e)}
        
def results_formatter(state: AgentState) -> AgentState:
    try:
        # If previous agent failed, return error instead of hallucinating
        if state.get("error") or not state.get("raw_results"):
            return {**state, "final_answer": "Sorry, I could not retrieve data for that question. Please try rephrasing it."}

        prompt = f"""
        You are a helpful data analyst assistant.
        The user asked: {state["question"]}
        Here are the raw results: {state["raw_results"]}
        Write a clear, friendly, professional answer.
        Do not mention SQL or technical details.
        """
        response = llm.invoke([HumanMessage(content=prompt)])
        final_answer = response.content.strip()

        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO query_history (username, question, sql_query, answer, timestamp)
                VALUES (:username, :question, :sql_query, :answer, :timestamp)
            """), {
                "username":  state["username"],
                "question":  state["question"],
                "sql_query": state["sql_query"],
                "answer":    final_answer,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            conn.commit()
        return {**state, "final_answer": final_answer}
    except Exception as e:
        return {**state, "error": str(e)}
# ════════════════════════════════════════════════════════
# 5. LANGGRAPH PIPELINE
# ════════════════════════════════════════════════════════

graph = StateGraph(AgentState)
graph.add_node("schema_reader",     schema_reader)
graph.add_node("sql_generator",     sql_generator)
graph.add_node("sql_executor",      sql_executor)
graph.add_node("results_formatter", results_formatter)
graph.add_edge("schema_reader",     "sql_generator")
graph.add_edge("sql_generator",     "sql_executor")
graph.add_edge("sql_executor",      "results_formatter")
graph.add_edge("results_formatter", END)
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
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO users (username, password_hash, created_at)
                VALUES (:username, :password_hash, :created_at)
            """), {
                "username":      username,
                "password_hash": hash_password(password),
                "created_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            conn.commit()
        return {"success": True, "message": f"User {username} registered successfully!"}
    except:
        return {"success": False, "message": "Username already exists."}

def login_user(username: str, password: str) -> dict:
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id, username FROM users
                WHERE username = :username AND password_hash = :password_hash
            """), {"username": username, "password_hash": hash_password(password)})
            row = result.fetchone()
        if row:
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
        "raw_data":     "",        # ← add this
        "final_answer": "",
        "error":        ""
    })
    return {
        "question":  request.question,
        "answer":    result["final_answer"],
        "sql_query": result["sql_query"],
        "raw_data":  json.loads(result["raw_data"]) if result.get("raw_data") else []  
    }

@app.get("/history/{username}")
def get_history(username: str):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT question, answer, timestamp
            FROM query_history
            WHERE username = :username
            ORDER BY timestamp DESC
        """), {"username": username})
        rows = result.fetchall()
    return [{"question": r[0], "answer": r[1], "timestamp": r[2]} for r in rows]

# ════════════════════════════════════════════════════════
# 8. RUN SERVER
# ════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
