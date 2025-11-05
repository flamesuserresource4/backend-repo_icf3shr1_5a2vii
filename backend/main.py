import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

from database import db, create_document, get_documents
from schemas import Message

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = Field(...)
    prompt: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    content: str


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}


@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Create a simple assistant reply, store both messages, return assistant content."""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt cannot be empty")

    # Store user message
    user_msg = Message(session_id=req.session_id, role="user", content=req.prompt.strip())
    try:
        create_document("message", user_msg)
    except Exception:
        # If db isn't available, continue without persistence
        pass

    # Very simple assistant response (no external APIs)
    assistant_text = (
        "Got it. I’ll start with a floating, glassy layout — hero, primary CTA, and a clean design system. "
        "Then I’ll scaffold screens and routes. Want me to generate the initial components now?"
    )

    assistant_msg = Message(session_id=req.session_id, role="assistant", content=assistant_text)
    try:
        create_document("message", assistant_msg)
    except Exception:
        pass

    return ChatResponse(content=assistant_text)


@app.get("/chat/{session_id}", response_model=List[Message])
def history(session_id: str):
    """Return recent messages for a session."""
    try:
        docs = get_documents("message", {"session_id": session_id}, limit=50)
        # Convert ObjectId and datetime to strings for JSON (pydantic will handle basic types)
        # Map to Message model
        parsed: List[Message] = []
        for d in docs:
            parsed.append(Message(session_id=d.get("session_id", ""), role=d.get("role", "assistant"), content=d.get("content", "")))
        return parsed
    except Exception:
        # If DB unavailable, return empty
        return []


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
