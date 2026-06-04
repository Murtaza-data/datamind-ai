# DataMind AI - Intelligent Data Analyst

An AI-powered data analyst that converts plain English questions into SQL queries using a multi-agent LangGraph pipeline, FastAPI backend, and Streamlit frontend.

## Live Demo
- Frontend: https://datamind-ai-bmzbmbz4itgvehf5lequrt.streamlit.app/
- Backend API: https://datamind-ai-umrm.onrender.com/docs

## What It Does
Users ask business questions in plain English. The system converts them into SQL queries, runs them against a real e-commerce database with 100,000+ orders, and returns clear answers.

## Example Questions
- What are the top 5 product categories by sales?
- Which city has the most orders?
- What is the total revenue from all payments?

## Tech Stack
- Frontend: Streamlit
- Backend: FastAPI
- Agents: LangGraph (4 agents)
- LLM: Groq LLaMA 3.1-8b-instant
- Database: SQLite
- Deployment: Render and Streamlit Cloud

## Multi-Agent Pipeline
1. Schema Reader - Reads database structure
2. SQL Generator - Converts question to SQL
3. SQL Executor - Runs SQL on database
4. Results Formatter - Returns friendly answer

## API Endpoints
- POST /register - Create new account
- POST /login - Login
- POST /ask - Ask a question
- GET /history/username - Get query history

## Authentication
- Register and login with username and password
- Passwords hashed with SHA-256
- Each user has their own query history

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
3. Add Groq API key: set GROQ_API_KEY=your_key
4. Run backend: python main.py
5. Run frontend: streamlit run app.py

## Environment Variables
- GROQ_API_KEY: Your Groq API key from console.groq.com
