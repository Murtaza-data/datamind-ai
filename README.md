# DataMind AI — Intelligent Data Analyst

An AI-powered data analyst that converts plain English questions into SQL queries using a multi-agent LangGraph pipeline, FastAPI backend, and Streamlit frontend.


## 🚀 Live Demo
**👉 [Try it here](https://datamind-ai-bmzbmbz4itgvehf5lequrt.streamlit.app/)**

## What It Does
Users ask business questions in plain English. The system converts them into SQL queries, runs them against a real e-commerce database with 100,000+ orders, and returns clear answers with automatic data visualizations.

## Tech Stack
- **Frontend:** Streamlit
- **Backend:** FastAPI
- **Agents:** LangGraph (4-agent pipeline)
- **LLM:** Groq LLaMA 3.3-70b-versatile
- **Database:** PostgreSQL (Supabase)
- **Visualizations:** Plotly Express
- **Deployment:** Render (backend) + Streamlit Cloud (frontend)

## Multi-Agent Pipeline
1. **Schema Reader** — Reads live database structure so the LLM knows what tables and columns exist
2. **SQL Generator** — Converts plain English question into a valid PostgreSQL query
3. **SQL Executor** — Runs the query against the database and retrieves results
4. **Results Formatter** — Converts raw data into a clear, friendly answer

## Smart Visualizations
The app automatically selects the best chart type based on the question:
- **Vertical bar chart** — for top/best/highest questions (blue gradient)
- **Horizontal bar chart** — for least/lowest/worst questions or many results (red gradient)
- **Line chart** — for trend/monthly/yearly questions
- **Pie chart** — for distribution/share/breakdown questions

## API Endpoints
- `POST /register` — Create new account
- `POST /login` — Login
- `POST /ask` — Ask a question, returns answer + SQL query + raw data
- `GET /history/{username}` — Get user query history

## Authentication
- Register and login with username and password
- Passwords hashed with SHA-256
- Each user has their own persistent query history
- Data persists across server restarts (PostgreSQL on Supabase)

## Database
Olist Brazilian E-Commerce Dataset from Kaggle
- 99,441 customers
- 99,441 orders
- 112,650 order items
- 32,951 products
- 103,886 payments

## How To Run Locally
1. Clone the repo: git clone https://github.com/Murtaza-data/datamind-ai.git
2. Install dependencies: pip install -r requirements.txt
3. Set environment variables: 
GROQ_API_KEY=your_groq_api_key, 
DATABASE_URL=your_postgresql_connection_string
4. Run backend: python main.py
5. Run frontend: streamlit run app.py


## Environment Variables
| Variable | Description |
|---|---|
| GROQ_API_KEY | Your Groq API key from console.groq.com |
| DATABASE_URL | PostgreSQL connection string (Supabase or any PostgreSQL provider) |   
