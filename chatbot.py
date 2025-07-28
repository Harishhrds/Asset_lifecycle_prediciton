import os
from flask import jsonify,Flask,request
from flask_cors import CORS
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
CORS(app)
openai_api_key = os.getenv("OPENAI_API_KEY")

loader = PyPDFLoader(r"C:\Users\Lenovo\Desktop\chatbot\Asset Chatbot.pdf")
docs = loader.load()


splitter = RecursiveCharacterTextSplitter(chunk_size=1000,chunk_overlap=200)
chunks = splitter.split_documents(docs)

# create chromdb
db = Chroma.from_documents(chunks,embedding=OpenAIEmbeddings())
retriever = db.as_retriever()

# 4. Create QA Chain
qa = RetrievalQA.from_chain_type(
    llm=ChatOpenAI(model="gpt-3.5-turbo"),
    chain_type="stuff",
    retriever=retriever
)
@app.route("/")
def home():
    return "Chatbot is running. POST your questions to `/chat`"

@app.route("/chat",methods=["POST"])
def chat():
    user_msg = request.json["message"]
    result=qa.run(user_msg)
    return jsonify({"reply":result})
if __name__ =="__main__":
    app.run(debug=True)


