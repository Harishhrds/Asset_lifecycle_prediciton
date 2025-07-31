from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
import pickle
import pandas as pd
import numpy as np
from dotenv import load_dotenv
import psycopg2
import os
import requests
import tempfile

# LangChain setup
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__, template_folder='templates')
app.secret_key = "SanathWonder2466"
CORS(app)

# Load ML model
model_path = "asset_life.pkl"
with open(model_path, 'rb') as file:
    model = pickle.load(file)

# PostgreSQL connection
conn = psycopg2.connect(
    host=os.getenv('PGHOST'),
    port=os.getenv('PGPORT'),
    user=os.getenv('PGUSER'),
    password=os.getenv('PGPASSWORD'),
    dbname=os.getenv('PGDATABASE')
)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS pdf_files(
               id SERIAL PRIMARY KEY,
               name TEXT UNIQUE,
               content BYTEA
               )""")
conn.commit()
cursor.close()
conn.close()
def store_pdf_to_postgres(pdf_path,pdf_name):
    with open(pdf_path,'rb') as file:
        binary_data = file.read()
    cursor.execute("""INSERT INTO pdf_files(name,content) 
                  values (%s,%s) ON CONFLICT(name) 
                  Do UPDATE SET content= EXCLUDE.content
                  """,(pdf_name,binary_data))
    conn.commit()
    cursor.close()
    conn.close()

# Example
store_pdf_to_postgres("Asset Chatbot.pdf", "Asset_Chatbot")
    
    

def load_pdf_from_postgres(pdf_name):

    cursor = conn.cursor()
    cursor.execute("SELECT content FROM pdf_files WHERE name = %s", (pdf_name,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        raise ValueError("PDF not found in database")

    pdf_binary = result[0]

    # Save to temp file (e.g. /tmp on Render)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_binary)
        temp_path = temp_file.name

    return temp_path

# Example
pdf_path = load_pdf_from_postgres("Asset_Chatbot")
loader = PyPDFLoader(pdf_path)
docs = loader.load()
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)
db = Chroma.from_documents(chunks, embedding=OpenAIEmbeddings())
retriever = db.as_retriever()
qa = RetrievalQA.from_chain_type(llm=ChatOpenAI(model="gpt-3.5-turbo"), chain_type="stuff", retriever=retriever)

# Chat endpoint
@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json["message"]
    result = qa.run(user_msg)
    return jsonify({"reply": result})

# User signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone_number')
        username = request.form.get('username')
        password = request.form.get('password')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        if user:
            flash("User Already Exists! Choose Another One")
            return render_template("signup.html")
        cur.execute("INSERT INTO users(full_name,phone,username,password) VALUES(%s,%s,%s,%s)",
                    (full_name, phone, username, password))
        conn.commit()
        cur.close()
        flash("Signup Successful. Please login")
        return redirect(url_for('login'))
    return render_template('signup.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cur.fetchone()
        cur.close()
        if user:
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')

# Main page
@app.route('/')
def home():
    if "username" in session:
        return render_template('index.html')
    return redirect(url_for('login'))

# Predict asset lifecycle
@app.route('/predict', methods=['POST'])
def predic():
    if not "username" in session:
        return redirect(url_for('login'))
    feature_names = [
        'asset_age_years',
        'total_usage_hours',
        'num_repairs',
        'last_maintenance_gap_days',
        'performance_score'
    ]
    values = [float(x) for x in request.form.values()]
    input_df = pd.DataFrame([values], columns=feature_names)
    prediction = model.predict(input_df)
    prediction_value = round(prediction[0], 2)
    return render_template('index.html', prediction_text=f"prediction_value: {prediction_value}")

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
