from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.data_loader import kb
from app.services.analyze_service import analyze_word


app = FastAPI(
    title="WAZN Arabic Learning API",
    description="Backend API for Arabic root, pattern, and word-family learning.",
    version="0.2.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://wazn-theta.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event() -> None:
    kb.load()


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/api/analyze")
def analyze(word: str = Query(..., min_length=1)):
    return analyze_word(word)

# @app.get("/debug/patterns")
# def debug_patterns():
#     return {
#         pattern_id: [
#             {
#                 "id": word.get("id"),
#                 "arabic": word.get("arabic"),
#                 "meaning": word.get("meaning"),
#             }
#             for word in words
#         ]
#         for pattern_id, words in kb.words_by_pattern.items()
#     }