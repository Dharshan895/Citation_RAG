import os
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


# =========================
# EMBEDDING MODEL
# =========================
embedding_model = HuggingFaceEmbeddings(
    model_name="BAAI/bge-base-en-v1.5",
    encode_kwargs={"normalize_embeddings": True},
    # You can upgrade to "BAAI/bge-large-en-v1.5" later for better quality
)


def extract_paper_metadata(docs):
    """Extract title and authors from first few pages"""
    title = "Unknown Title"
    authors = "Unknown Authors"
    
    for doc in docs[:3]:  # Check first 3 pages
        text = doc.page_content.lower()
        if "title" in text or len(text.split()) < 50:  # Likely title page
            lines = doc.page_content.split("\n")
            title = lines[0].strip() if lines else title
            # Simple author extraction (can be improved)
            for line in lines[:10]:
                if "@" not in line and len(line) < 150 and any(char.isalpha() for char in line):
                    authors = line.strip()
                    break
    return title, authors


def make_embedding(input_document: str, chroma_path: str):
    """
    Process PDF and create embeddings with improved chunking
    """
    try:
        # =========================
        # LOAD PDF (Better Loader)
        # =========================
        loader = PyMuPDFLoader(input_document)
        document = loader.load()

        # Add basic metadata to each page
        for page_num, doc in enumerate(document):
            doc.metadata["page"] = page_num + 1
            doc.metadata["source"] = os.path.basename(input_document)

        # Extract paper-level metadata
        paper_title, paper_authors = extract_paper_metadata(document)
        
        for doc in document:
            doc.metadata["paper_title"] = paper_title
            doc.metadata["authors"] = paper_authors

        # =========================
        # IMPROVED TEXT SPLITTING
        # =========================
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,          # Increased
            chunk_overlap=300,        # Increased
            separators=[
                "\n\n\n",    # Paragraphs
                "\n\n",
                "\n",
                ". ",
                " ",
                ""
            ],
            length_function=len,
        )

        chunks = text_splitter.split_documents(document)

        # Add chunk IDs
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = i
            chunk.metadata["total_chunks"] = len(chunks)

        # =========================
        # STORE IN CHROMA
        # =========================
        Chroma.from_documents(
            documents=chunks,
            embedding=embedding_model,
            persist_directory=chroma_path
        )

        return {
            "status": "success",
            "total_chunks": len(chunks),
            "paper_title": paper_title,
            "paper_authors": paper_authors
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }