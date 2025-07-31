import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pymysql
from pymongo import MongoClient
import redis
import openai

# Configuration from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "password")
MYSQL_DB = os.getenv("MYSQL_DB", "test")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "test")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

mysql_conn = pymysql.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB,
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True
)

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_mysql_schema():
    """Retrieve all table and field info (RAG for MySQL)"""
    schema_info = {}
    with mysql_conn.cursor() as cursor:
        cursor.execute("SHOW TABLES;")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        for tbl in tables:
            cursor.execute(f"SHOW COLUMNS FROM `{tbl}`;")
            columns = [row["Field"] for row in cursor.fetchall()]
            schema_info[tbl] = columns
    return schema_info

def get_mongo_schema():
    """Get sample collections and fields (RAG for MongoDB)"""
    schema_info = {}
    colls = mongo_db.list_collection_names()
    for coll in colls:
        sample = mongo_db[coll].find_one()
        schema_info[coll] = list(sample.keys()) if sample else []
    return schema_info

def nlp_to_query(question, db_type, schema_info):
    """Use OpenAI LLM with schema RAG in the prompt."""
    prompt = f"""You are an expert database assistant.
Here is information about the database schema:
{json.dumps(schema_info, indent=2)}

User question: {question}
Convert it into a {db_type.upper()} query. If MongoDB, give a Python dictionary-style code suitable for PyMongo find/aggregate, not raw shell syntax.

Return ONLY the query (for MongoDB as a dict, for SQL as a query string), nothing else."""
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a database assistant."},
            {"role": "user", "content": prompt}
        ],
        api_key=OPENAI_API_KEY,
        temperature=0.1
    )
    reply = response['choices'][0]['message']['content']
    # Strip code fences, if any
    if reply.startswith("```
        reply = reply.strip().split("```")[1].strip()
    # Try to parse MongoDB dict if needed
    if db_type.lower() == "mongodb":
        try:
            # Eval is unsafe! For production, require JSON output and parse JSON.
            query_obj = eval(reply, {"__builtins__": {}})
            return query_obj
        except Exception as e:
            raise Exception(f"Error parsing MongoDB query: {e}\nLLM Output: {reply}")
    return reply.strip()

@app.post("/query")
async def query(request: dict):
    question = request.get("question", "")
    db_type = request.get("db_type", "")
    schema = request.get("schema", "")

    cache_key = f"{db_type}:{question}"
    cached = redis_client.get(cache_key)
    if cached:
        return {"results": json.loads(cached.decode())}

    try:
        # RAG: Fetch live schema!
        if db_type.lower() == "mysql":
            schema_info = get_mysql_schema()
        elif db_type.lower() == "mongodb":
            schema_info = get_mongo_schema()
        else:
            raise HTTPException(400, "Unsupported DB type")

        db_query = nlp_to_query(question, db_type, schema_info)
        if db_type.lower() == "mysql":
            with mysql_conn.cursor() as cursor:
                cursor.execute(db_query)
                results = cursor.fetchall()
        elif db_type.lower() == "mongodb":
            # Example expects {"find": <collection>, ...} or {"aggregate": ...}
            if isinstance(db_query, dict):
                if "find" in db_query:
                    collection = db_query.get("find")
                    filter_ = db_query.get("filter", {})
                    res = mongo_db[collection].find(filter_)
                    results = list(res)
                elif "aggregate" in db_query:
                    collection = db_query.get("aggregate")
                    pipeline = db_query.get("pipeline", [])
                    res = mongo_db[collection].aggregate(pipeline)
                    results = list(res)
                else:
                    results = {"error": "Unsupported MongoDB command from LLM.", "query": db_query}
                for r in results:
                    if "_id" in r:
                        r["_id"] = str(r["_id"])
            else:
                results = {"error": "LLM did not return a valid MongoDB query.", "query": db_query}
        else:
            raise HTTPException(400, "Unknown DB type")
        redis_client.set(cache_key, json.dumps(results))
        return {"results": results}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
