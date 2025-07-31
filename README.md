# ChatDB: NLP-Powered Database Query Engine

ChatDB empowers users to ask questions and make changes in SQL (MySQL) or NoSQL (MongoDB) databases using **conversational English**—no SQL required.

---

## Features

- Query MySQL & MongoDB via plain English
- Automatic translation of user requests to SQL and MongoDB queries
- Returns results instantly, with caching for fast repeated questions
- Simple Streamlit web interface for chatting with your database

---

## Quickstart

### 1. Requirements

- Python 3.8+
- Running MySQL and/or MongoDB instances
- Optional: Redis for caching (defaults to localhost)
- All required packages can be installed via pip

### 2. Installation

Install Python dependencies:


### 3. Environment setup

Set environment variables or edit connection info in `app.py`:


### 4. Run the Backend


### 5. Run the Frontend


---

## Usage

1. Open the Streamlit app.
2. Select "mysql" or "mongodb".
3. Ask questions like:
   - MySQL: `List all customers who ordered in 2024.`
   - MongoDB: `Find users with more than 10 purchases.`
4. See results instantly!

---

## Notes

- The LLM + RAG logic is fully included, using schema/context and OpenAI GPT-4o.
- For production, make `nlp_to_query()` handle output parsing more robustly and add authentication.
- Never eval() untrusted LLM code in production; prefer safe JSON outputs.

---



