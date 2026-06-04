# 🧠 DataMind AI — Intelligent Data Analyst
An AI-powered data analyst that converts plain English questions into SQL queries using a multi-agent LangGraph pipeline, FastAPI backend, and Streamlit frontend.
## 🚀 Live Demo
- **Frontend:** [Streamlit App](https://datamind-ai-bmzbmbz4itgvehf5lequrt.streamlit.app/)
- **Backend API:** [Render API](https://datamind-ai-umrm.onrender.com/docs)
## 📌 What It Does
Users ask business questions in plain English — the system automatically converts them into SQL queries, runs them against a real e-commerce database with 100,000+ orders, and returns clear, professional answers.
**Example questions:**
- "What are the top 5 product categories by sales?"
- "Which city has the most orders?"
- "What is the total revenue from all payments?"
## 🏗️ Architecture
User → Streamlit Frontend
↓
FastAPI Backend (Render)
↓
LangGraph Multi-Agent Pipeline
├── Agent 1: Schema Reader
├── Agent 2: SQL Generator
├── Agent 3: SQL Executor
└── Agent 4: Results Formatter
↓
SQLite Database (Olist Dataset)

## 🤖 Multi-Agent Pipeline
The system uses 4 specialized AI agents working in sequence:
| Agent | Job |
|---|---|
| Schema Reader | Reads database structure — tables and columns |
| SQL Generator | Converts English question into SQL query using LLM |
| SQL Executor | Runs SQL query on the database, gets raw results |
| Results Formatter | Converts raw results into a friendly readable answer |
## 🗄️ Database
Uses the **Olist Brazilian E-Commerce Dataset** (Kaggle) with 100,000+ real orders.
**Tables:**
- `customers` — 99,441 customers
- `orders` — 99,441 orders
- `order_items` — 112,650 items
- `products` — 32,951 products
- `payments` — 103,886 payments
- `users` — registered app users
- `query_history` — saved questions and answers per user
## 🔐 Authentication
- Users register with username and password
- Passwords are hashed using SHA-256 — never stored as plain text
- Each user has their own query history
- Session management handled by Streamlit session state
## 🛠️ Tech Stack
| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend | FastAPI |
| Agents | LangGraph |
| LLM | Groq (LLaMA 3.1-8b-instant) |
| Database | SQLite |
| Deployment | Render (backend) + Streamlit Cloud (frontend) |
## 📡 API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/register` | Create new user account |
| POST | `/login` | Login with username and password |
| POST | `/ask` | Ask a question — runs full agent pipeline |
| GET | `/history/{username}` | Get query history for a user |
## 📁 Project Structure
datamind-ai/
├── main.py ← FastAPI backend + agents + database
├── app.py ← Streamlit frontend
├── requirements.txt ← Python dependencies
├── olist_customers_dataset.csv ← Customer data
├── olist_orders_dataset.csv ← Orders data
├── olist_order_items_dataset.csv ← Order items data
├── olist_products_dataset.csv ← Products data
├── olist_order_payments_dataset.csv ← Payments data
└── product_category_name_translation.csv ← Portuguese to English translation

## ⚙️ How To Run Locally
**1. Clone the repository:**
```bash
git clone https://github.com/Murtaza-data/datamind-ai.git
cd datamind-ai
2. Install dependencies:

pip install -r requirements.txt
3. Add your Groq API key:

export GROQ_API_KEY="your_groq_api_key"
4. Run the FastAPI backend:

python main.py
5. Run the Streamlit frontend:

streamlit run app.py
🔑 Environment Variables
Variable	Description
GROQ_API_KEY	Your Groq API key from console.groq.com
