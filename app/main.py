from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.agent import process_chat
from app.schemas import ChatRequest, ChatResponse


app = FastAPI(title="Coach RAG API")

# -------------------------
#  CORS
# -------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
#  ENDPOINT CHAT
# -------------------------
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        result = await process_chat(req)
        return ChatResponse(reply=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------
#  MODE STANDALONE
# -------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
