from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from app.data_loader import kb
from app.services.analyze_service import analyze_word
from app.services.insights_service import (
    build_insights_response,
    build_pipeline_state,
    build_sentence_response,
)
from app.services.k2_agents_service import prewarm_insights


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
        # Dev machine's LAN address, so other devices on the same network
        # can open the Vite dev server and still reach this backend.
        "http://192.168.8.39:5173",
        "https://wazn-peach.vercel.app",
    ],
    # Vercel gives every preview deploy its own generated subdomain, so a branch
    # preview is blocked by the fixed list above and looks like a dead backend.
    # Scoped to this project's previews — not a wildcard.
    allow_origin_regex=r"https://wazn-[a-z0-9-]+\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event() -> None:
    kb.load()

    # No-op unless ENABLE_K2_INSIGHTS_PREWARM is set — it runs four sequential
    # K2 calls per word before the app serves traffic, which is the point.
    outcomes = prewarm_insights(state_builder=build_pipeline_state)
    if outcomes:
        print(f"[insights prewarm] {outcomes}")


@app.get("/ping")
def ping():
    return {"status": "ok"}


@app.get("/api/analyze")
def analyze(word: str = Query(..., min_length=1)):
    return analyze_word(word)


@app.get("/api/insights")
def insights(word: str = Query(..., min_length=1)):
    return build_insights_response(word)


@app.get("/api/sentence")
def sentence(word: str = Query(..., min_length=1)):
    # The sentence agent alone — the Details tab asks per displayed leaf, and
    # waiting on the full insights chain would hold the section for 15-45s.
    return build_sentence_response(word)

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