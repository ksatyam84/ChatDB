import streamlit as st
import requests

st.set_page_config(page_title="ChatDB", page_icon="💬")
st.title("ChatDB: Natural Language DB Chatbot")

db_type = st.selectbox("Select database", ("mysql", "mongodb"))
query = st.text_area("Ask your database anything:")

if st.button("Submit"):
    with st.spinner("Querying..."):
        resp = requests.post(
            "http://localhost:8000/query",
            json={"question": query, "db_type": db_type}
        )
        data = resp.json()
        if "results" in data:
            st.json(data["results"])
        else:
            st.error(data.get("error", "Unknown error"))
