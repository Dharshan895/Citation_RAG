import os
from dotenv import load_dotenv

from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.chat_message_histories import FileChatMessageHistory  # ← Fixed Import

from embedding import embedding_model

# =========================
# LOAD ENVIRONMENT
# =========================
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

# =========================
# LOAD LLM
# =========================
llm = ChatGroq(
    api_key=groq_api_key,
    model="llama-3.1-8b-instant",
    temperature=0.1,
    max_tokens=800
)


def rewrite_query(query: str) -> str:
    """Improve query for better retrieval"""
    prompt = f"""You are an expert at reformulating questions for academic paper retrieval.
Rephrase the following user query to be more precise, formal, and effective for semantic search in a research paper.

Original Query: {query}

Rephrased Query:"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except:
        return query  # Fallback


def get_reply(session_id: str, message: str):
    # =========================
    # CHROMA PATH
    # =========================
    chroma_path = os.path.join("chat_sessions", session_id, "chroma_db")

    if not os.path.exists(chroma_path):
        return "No document has been uploaded for this session."

    # =========================
    # LOAD VECTOR STORE
    # =========================
    vectorstore = Chroma(
        persist_directory=chroma_path,
        embedding_function=embedding_model
    )

    # =========================
    # QUERY REWRITING
    # =========================
    rewritten_query = rewrite_query(message)

    # =========================
    # SPECIAL HANDLING + RETRIEVAL
    # =========================
    lower_msg = message.lower().strip()

    if any(word in lower_msg for word in ["title", "name of the paper", "paper title"]):
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4, "filter": {"chunk_id": {"$lte": 5}}}
        )
    elif any(word in lower_msg for word in ["author", "authors", "who wrote", "written by"]):
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 6}
        )
    else:
        retriever = vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 12}
        )

    # =========================
    # RETRIEVE DOCUMENTS
    # =========================
    docs = retriever.invoke(rewritten_query)

    if not docs:
        return "The uploaded paper does not contain enough information."

    # =========================
    # BUILD CONTEXT WITH CITATIONS
    # =========================
    context_parts = []
    for i, doc in enumerate(docs):
        page = doc.metadata.get("page", "N/A")
        context_parts.append(
            f"[Source {i+1}] (Page {page})\n"
            f"{doc.page_content.strip()}\n"
        )

    context = "\n---\n".join(context_parts)

    # =========================
    # LOAD CHAT HISTORY (Improved)
    # =========================
    history_path = os.path.join("chat_sessions", session_id, "chat_history.json")
    
    if os.path.exists(history_path):
        chat_history = FileChatMessageHistory(history_path)
        recent_history = chat_history.messages[-6:]   # Increased a bit
    else:
        recent_history = []

    # =========================
    # FINAL PROMPT
    # =========================
    system_prompt = SystemMessage(
        content="""
You are an expert research assistant helping users understand academic papers.

Rules:
- Answer ONLY using the provided context.
- Be direct, concise, and accurate.
- When using information from context, cite it as [Source X].
- For title or author questions, give very short and direct answers.
- If the answer is not clearly in the context, respond with: "The uploaded paper does not contain enough information."
- Do not hallucinate or add external knowledge.
"""
    )

    context_message = SystemMessage(
        content=f"CONTEXT FROM RESEARCH PAPER:\n\n{context}"
    )

    messages = [
        system_prompt,
        *recent_history,
        context_message,
        HumanMessage(content=message)
    ]

    # =========================
    # GENERATE RESPONSE
    # =========================
    response = llm.invoke(messages)

    # Optional: Save the new message to history
    try:
        if os.path.exists(history_path):
            chat_history.add_user_message(message)
            chat_history.add_ai_message(response.content)
        else:
            # Create new history
            new_history = FileChatMessageHistory(history_path)
            new_history.add_user_message(message)
            new_history.add_ai_message(response.content)
    except:
        pass  # Don't break if history saving fails

    return response.content