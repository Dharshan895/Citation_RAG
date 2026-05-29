from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from fastapi.staticfiles import StaticFiles
import uuid
import json
from embedding import make_embedding
from langchain_core.messages import HumanMessage, AIMessage
from langchain_community.chat_message_histories import FileChatMessageHistory
from answering_rag_bot import get_reply

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
class ChatRequest(BaseModel):
    session_id: str
    message: str

BASE_DIR = "chat_sessions"

if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):

    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files allowed"
        )

    # Create unique session
    session_id = str(uuid.uuid4())

    # Main session folder
    session_folder = os.path.join(BASE_DIR, session_id)
    os.makedirs(session_folder, exist_ok=True)

    # Chroma DB folder
    chroma_folder = os.path.join(session_folder, "chroma_db")
    os.makedirs(chroma_folder, exist_ok=True)

    # PDF storage folder
    pdf_folder = os.path.join(session_folder, "pdf_folder")
    os.makedirs(pdf_folder, exist_ok=True)

    # Save uploaded PDF
    pdf_path = os.path.join(pdf_folder, file.filename)

    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Empty chat history
    chat_history_path = os.path.join(
        session_folder,
        "chat_history.json"
    )

    with open(chat_history_path, "w") as f:
        json.dump([], f, indent=4)

    # Create embeddings
    status_message = make_embedding(
        pdf_path,
        chroma_folder
    )

    # Handle failure
    if status_message["status"] == "error":

        shutil.rmtree(session_folder)

        raise HTTPException(
            status_code=500,
            detail=status_message["message"]
        )

    return {
        "status": "success",
        "message": "Ask anything about the PDF",
        "session_id": session_id
    }

@app.post("/chat")
async def chat(req: ChatRequest):

    session_id = req.session_id
    message = req.message

    # Check session ID
    if not session_id:
        return {
            "reply": "No PDF uploaded"
        }

    # Session folder
    session_folder = os.path.join(BASE_DIR, session_id)

    if not os.path.exists(session_folder):
        return {
            "reply": "Invalid session"
        }

    # Chat history file
    history_path = os.path.join(
        session_folder,
        "chat_history.json"
    )

    # Load history
    chat_history = FileChatMessageHistory(history_path)


    # Generate reply
    reply = get_reply(
        session_id=session_id,
        message=message
    )

    # Store user message
    chat_history.add_message(
        HumanMessage(content=message)
    )

    # Store AI reply
    chat_history.add_message(
        AIMessage(content=reply)
    )

    return {
        "reply": reply
    }
app.mount("/",StaticFiles(directory=".",html = True),name = "static")